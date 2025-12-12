import random
import pygame
from os import listdir
from os.path import isfile, join

pygame.init()
pygame.display.set_caption("TerraLeap")

WIDTH, HEIGHT = 800, 600
FPS = 60
PLAYER_VEL = 5

window = pygame.display.set_mode((WIDTH, HEIGHT))


def flip(sprites):
    return [pygame.transform.flip(sprite, True, False) for sprite in sprites]


def load_sprites_sheets(dir1, dir2, width, height, direction=False):
    path = join("assets", dir1, dir2)
    images = [f for f in listdir(path) if isfile(join(path, f))]
    sheets = {}

    for image in images:
        sprite_sheet = pygame.image.load(join(path, image)).convert_alpha()
        frames = []

        for i in range(sprite_sheet.get_width() // width):
            surf = pygame.Surface((width, height), pygame.SRCALPHA)
            rect = pygame.Rect(i * width, 0, width, height)
            surf.blit(sprite_sheet, (0, 0), rect)
            frames.append(pygame.transform.scale2x(surf))

        name = image.replace(".png", "")
        if direction:
            sheets[name + "_right"] = frames
            sheets[name + "_left"] = flip(frames)
        else:
            sheets[name] = frames

    return sheets


def get_block(size):
    img = pygame.image.load(join("assets", "Terrain", "Terrain.png"))
    img = img.convert_alpha()

    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    rect = pygame.Rect(96, 0, size, size)
    surf.blit(img, (0, 0), rect)

    return pygame.transform.scale2x(surf)


def remove_white_background(img):
    img = img.convert_alpha()
    w, h = img.get_size()

    for x in range(w):
        for y in range(h):
            r, g, b, a = img.get_at((x, y))
            if r > 180 and g > 180 and b > 180:
                img.set_at((x, y), (255, 255, 255, 0))

    return img



class Player(pygame.sprite.Sprite):
    GRAVITY = 1
    SPRITES = load_sprites_sheets("MainCharacters", "PinkMan", 32, 32, True)
    ANIMATION_DELAY = 3

    def __init__(self, x, y, w, h):
        super().__init__()
        self.rect = pygame.Rect(x, y, w, h)
        self.x_vel = 0
        self.y_vel = 0
        self.mask = None
        self.direction = "left"
        self.fall_count = 0
        self.jump_count = 0
        self.animation_count = 0
        self.hit = False
        self.hit_count = 0

    def jump(self):
        self.y_vel = -self.GRAVITY * 8
        self.jump_count += 1
        if self.jump_count == 1:
            self.fall_count = 0

    def move(self, dx, dy):
        self.rect.x += dx
        self.rect.y += dy

    def make_hit(self):
        self.hit = True
        self.hit_count = 0

    def move_left(self, vel):
        self.x_vel = -vel
        if self.direction != "left":
            self.direction = "left"
            self.animation_count = 0

    def move_right(self, vel):
        self.x_vel = vel
        if self.direction != "right":
            self.direction = "right"
            self.animation_count = 0

    def loop(self, fps):
        self.y_vel += min(1, (self.fall_count / fps) * self.GRAVITY)
        self.move(self.x_vel, self.y_vel)

        if self.hit:
            self.hit_count += 1
            if self.hit_count > fps * 2:
                self.hit = False

        self.fall_count += 1
        self.update_sprite()

    def landed(self):
        self.fall_count = 0
        self.y_vel = 0
        self.jump_count = 0

    def hit_head(self):
        self.y_vel *= -1

    def update_sprite(self):
        s = "idle"
        if self.hit:
            s = "hit"
        elif self.y_vel < 0:
            s = "jump" if self.jump_count == 1 else "double_jump"
        elif self.y_vel > self.GRAVITY * 2:
            s = "fall"

        if self.x_vel != 0:
            s = "run"

        sprites = self.SPRITES[s + "_" + self.direction]
        frame = (self.animation_count // self.ANIMATION_DELAY) % len(sprites)
        self.sprite = sprites[frame]
        self.animation_count += 1

        self.update()

    def update(self):
        x, y = self.rect.x, self.rect.y
        self.rect = self.sprite.get_rect(topleft=(x, y))
        self.mask = pygame.mask.from_surface(self.sprite)

    def draw(self, win, offset):
        win.blit(self.sprite, (self.rect.x - offset, self.rect.y))



class Object(pygame.sprite.Sprite):
    def __init__(self, x, y, w, h, name=None):
        super().__init__()
        self.rect = pygame.Rect(x, y, w, h)
        self.image = pygame.Surface((w, h), pygame.SRCALPHA)
        self.name = name

    def draw(self, win, offset):
        win.blit(self.image, (self.rect.x - offset, self.rect.y))


class Block(Object):
    def __init__(self, x, y, s):
        super().__init__(x, y, s, s)
        tile = get_block(s)
        self.image.blit(tile, (0, 0))
        self.mask = pygame.mask.from_surface(self.image)


class Fire(Object):
    DELAY = 3

    def __init__(self, x, y, w, h):
        super().__init__(x, y, w, h, "fire")
        self.frames = load_sprites_sheets("Traps", "Fire", w, h)
        self.anim = "on"
        self.count = 0
        self.image = self.frames["on"][0]
        self.mask = pygame.mask.from_surface(self.image)

    def loop(self):
        frames = self.frames[self.anim]
        idx = (self.count // self.DELAY) % len(frames)
        self.image = frames[idx]
        self.mask = pygame.mask.from_surface(self.image)
        self.count += 1


class Coin:
    def __init__(self, x, y, r=12):
        self.x = x
        self.y = y
        self.r = r
        self.collected = False
        self.image = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)

        pygame.draw.circle(self.image, (255, 215, 0), (r, r), r)
        pygame.draw.circle(self.image, (255, 240, 180), (r - 4, r - 6), r // 3)
        self.rect = self.image.get_rect(topleft=(x, y))

    def draw(self, win, offset):
        if not self.collected:
            win.blit(self.image, (self.x - offset, self.y))

    def check_collect(self, player):
        if not self.collected and self.rect.colliderect(player.rect):
            self.collected = True
            return True
        return False


def get_background(name):
    img = pygame.image.load(join("assets", "Background", name))
    w, h = img.get_size()
    tiles = [(i * w, j * h) for i in range(WIDTH // w + 1) for j in range(HEIGHT // h + 1)]
    return tiles, img


def draw(win, bg, bg_img, player, objects, offset):
    for tile in bg:
        win.blit(bg_img, tile)

    for obj in objects:
        obj.draw(win, offset)

    player.draw(win, offset)


HEART_IMG = remove_white_background(pygame.image.load(join("assets", "heart.png")))
TROPHY_IMG = pygame.image.load(join("assets", "end(idle).png")).convert_alpha()

LIVES = 3
GAME_OVER = False
SCORE = 0
LEVEL_END_X = 4000

FONT = pygame.font.SysFont("arial", 28)


def draw_lives(win, n):
    for i in range(n):
        win.blit(pygame.transform.scale(HEART_IMG, (40, 40)), (10 + i * 45, 10))


def draw_score(win, score):
    t = FONT.render(f"Score: {score}", True, (255, 255, 255))
    win.blit(t, (WIDTH - t.get_width() - 10, 10))


def draw_game_over(win):
    big = pygame.font.SysFont("arial", 46)
    t1 = big.render("GAME OVER", True, (255, 255, 255))
    t2 = FONT.render("Press R to Restart", True, (255, 255, 255))

    win.blit(t1, (WIDTH // 2 - t1.get_width() // 2, HEIGHT // 2 - 40))
    win.blit(t2, (WIDTH // 2 - t2.get_width() // 2, HEIGHT // 2 + 10))


def handle_vertical(player, objs, dy):
    hits = []

    for obj in objs:
        if pygame.sprite.collide_mask(player, obj):
            if dy > 0:
                player.rect.bottom = obj.rect.top
                player.landed()
            elif dy < 0:
                player.rect.top = obj.rect.bottom
                player.hit_head()

            hits.append(obj)

    return hits


def collide(player, objs, dx):
    player.move(dx, 0)
    player.update()

    hit = None
    for obj in objs:
        if pygame.sprite.collide_mask(player, obj):
            hit = obj
            break

    player.move(-dx, 0)
    player.update()
    return hit


def handle_move(player, objs):
    keys = pygame.key.get_pressed()
    player.x_vel = 0

    if keys[pygame.K_LEFT] and not collide(player, objs, -PLAYER_VEL * 2):
        player.move_left(PLAYER_VEL)

    if keys[pygame.K_RIGHT] and not collide(player, objs, PLAYER_VEL * 2):
        player.move_right(PLAYER_VEL)

    handle_vertical(player, objs, player.y_vel)


def main(window):
    global LIVES, GAME_OVER, SCORE

    clock = pygame.time.Clock()
    bg, bg_img = get_background("Pink.png")

    player = Player(100, 100, 50, 50)
    block_size = 96

    # Make floor
    floor = [Block(i * block_size, HEIGHT - block_size, block_size) for i in range(-10, 200)]
    objects = floor.copy()

    # Random elevated blocks
    for x in range(300, LEVEL_END_X, 600):
        objects.append(Block(x, HEIGHT - block_size * random.choice([2, 3, 4]), block_size))

    # Fires
    for x in range(500, LEVEL_END_X, 500):
        objects.append(Fire(x, HEIGHT - block_size - 64, 16, 32))

    # Coins
    coins = []
    for x in range(250, LEVEL_END_X, 400):
        y = random.choice([
            HEIGHT - block_size - 60,
            HEIGHT - block_size * 2 - 60,
            HEIGHT - block_size * 3 - 60
        ])
        coins.append(Coin(x, y))

    # Trophy
    trophy_rect = TROPHY_IMG.get_rect(topleft=(LEVEL_END_X, HEIGHT - block_size - 100))

    offset = 0
    scroll = 200

    running = True

    while running:
        clock.tick(FPS)


        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False

            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_SPACE and player.jump_count < 2 and not GAME_OVER:
                    player.jump()

                if GAME_OVER and e.key == pygame.K_r:
                    LIVES = 3
                    SCORE = 0
                    GAME_OVER = False

                    player.rect.x = 100
                    player.rect.y = 100
                    offset = 0
                    player.hit = False

                    for c in coins:
                        c.collected = False

        if GAME_OVER:
            draw(window, bg, bg_img, player, objects, offset)
            for c in coins:
                c.draw(window, offset)

            draw_lives(window, LIVES)
            draw_score(window, SCORE)
            window.blit(pygame.transform.scale(TROPHY_IMG, (60, 60)),
                        (trophy_rect.x - offset, trophy_rect.y))
            draw_game_over(window)
            pygame.display.update()
            continue

        #
        # PHYSICS ORDER
        #
        player.loop(FPS)

        for obj in objects:
            if isinstance(obj, Fire):
                obj.loop()

        handle_move(player, objects)
        handle_vertical(player, objects, player.y_vel)
        player.update()


        player_hitbox = pygame.Rect(
            player.rect.x + 2,        
            player.rect.y + 5,
            player.rect.width - 4,
            player.rect.height - 10
        )

        for obj in objects:
            if obj.name == "fire":
                fire_rect = obj.rect

                # No damage if standing directly on top
                if player.rect.bottom == fire_rect.top:
                    continue

                # If touching from left, right, or bottom → damage
                if player_hitbox.colliderect(fire_rect):
                    if not player.hit:
                        LIVES -= 1
                        player.make_hit()

                        if LIVES <= 0:
                            GAME_OVER = True
                        else:
                            player.x_vel = 0
                            player.y_vel = 0


        for c in coins:
            if c.check_collect(player):
                SCORE += 10

        
        if player.rect.x < offset - 300 or player.rect.x > offset + WIDTH + 300:
            LIVES -= 1
            if LIVES <= 0:
                GAME_OVER = True
            else:
                player.rect.x = 100
                player.rect.y = 100
                offset = 0

        
        draw(window, bg, bg_img, player, objects, offset)

        for c in coins:
            c.draw(window, offset)

        window.blit(pygame.transform.scale(TROPHY_IMG, (60, 60)),
                    (trophy_rect.x - offset, trophy_rect.y))

        draw_lives(window, LIVES)
        draw_score(window, SCORE)

        
        if player.rect.colliderect(trophy_rect):
            f = pygame.font.SysFont("arial", 42)
            t = f.render("YOU WIN!", True, (255, 255, 0))
            window.blit(t, (WIDTH // 2 - t.get_width() // 2, HEIGHT // 2))
            pygame.display.update()
            pygame.time.delay(1500)
            GAME_OVER = True

        
        if ((player.rect.right - offset >= WIDTH - scroll and player.x_vel > 0)
            or (player.rect.left - offset <= scroll and player.x_vel < 0)):
            offset += player.x_vel

        pygame.display.update()

    pygame.quit()



if __name__ == "__main__":
    main(window)
