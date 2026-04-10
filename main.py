import math
import pygame 
import random as rand
pygame.init()

HEIGHT = 800
WIDTH = 1400

black = (0,0,0)
white = (255, 255, 255)
sage = (163, 177,139)
green = (59, 91, 76)
reseda_green = (92,118, 80)
blue = (212, 175, 55)

screen = pygame.display.set_mode([WIDTH, HEIGHT])
pygame.display.set_caption("BCI Beat Maker")
label_font = pygame.font.SysFont('Arial', 30)
boot_font = pygame.font.SysFont('Courier New', 40, bold=True)


run = True
fps = 60
timer = pygame.time.Clock()
beats = 8
instruments = 6
boxes = []
clicked = [[-1 for _ in range(beats)] for _ in range(instruments)] # 2D list to keep track of which boxes have been clicked
bpm = 240
playing = True
active_length = 0
active_beat = 1
beat_changed = True

# load in sounds
hi_hat = pygame.mixer.Sound('wav_files/hi hat.WAV')
snare = pygame.mixer.Sound('wav_files/snare.WAV')
kick = pygame.mixer.Sound('wav_files/kick.WAV')
crash = pygame.mixer.Sound('wav_files/crash.wav')
clap = pygame.mixer.Sound('wav_files/clap.wav')
tom = pygame.mixer.Sound('wav_files/tom.WAV')
pygame.mixer.set_num_channels(instruments * 3) 

def boot_sequence():
    booting = True
    start_time = pygame.time.get_ticks()
    duration = rand.randint(4000, 5000)  # 4.5 seconds for the boot sequence

    point_one = []
    point_two = []
    point_three = []


    while booting:
        timer.tick(fps)
        current_time = pygame.time.get_ticks()
        elapsed = current_time - start_time

        if elapsed > duration + 1000: 
            booting = False
            continue

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
        
        screen.fill(black)

        if elapsed < duration:
            t = elapsed / 2 % 1400
            x = t
            y_one = math.sin(t/(rand.randint(25, 75))) * (rand.randint(10, 100)) + 200 # 50 is frequency, 100 is amplitude, 200 is vertical shift
            y_two = math.sin(t/(rand.randint(25, 75))) *  (rand.randint(10, 100)) + 400
            y_three = math.sin(t/(rand.randint(25, 75))) * (rand.randint(10, 100)) + 600

            point_one.append((x, y_one))
            point_two.append((x, y_two))
            point_three.append((x, y_three))

            if len(point_one) > 1:
                pygame.draw.circle(screen, (0,255,255), (x, y_one), 5)
            if len(point_two) > 1:
                pygame.draw.circle(screen, (0,255,255), (x, y_two), 5)
            if len(point_three) > 1:
                pygame.draw.circle(screen, (0,255,255), (x, y_three), 5)
            title_text = boot_font.render("Loading", True, white)
            
            screen.blit(title_text, (WIDTH//2 - title_text.get_width()//2, HEIGHT//2 - 20))
            
        else:
            if len(point_one) > 1:
                pygame.draw.circle(screen, (0,255,255), (x, y_one), 5)
            if len(point_two) > 1:
                pygame.draw.circle(screen, (0,255,255), (x, y_two), 5)
            if len(point_three) > 1:
                pygame.draw.circle(screen, (0,255,255), (x, y_three), 5)

            title_text = boot_font.render("Loading Complete", True, white)
            
            screen.blit(title_text, (WIDTH//2 - title_text.get_width()//2, HEIGHT//2 - 20))

        pygame.display.flip()

# Run the bootup sequence before loading the main interface
boot_sequence()



        


def play_notes():
    for i in range(len(clicked)):
        if clicked[i][active_beat] == 1:
            if i == 0:
                hi_hat.play()
            elif i == 1:
                snare.play()
            elif i == 2:
                kick.play()
            elif i == 3:
                crash.play()
            elif i == 4:
                clap.play()
            elif i == 5:
                tom.play()


def draw_grid(clicks, beat):
    left_box = pygame.draw.rect(screen, sage, (0,0,200,HEIGHT-200), 5)
    bottom_box = pygame.draw.rect(screen, white, (0, HEIGHT-200, WIDTH, 200), 5)
    boxes = []
    colors = [sage, white, sage]
    hi_hat_text = label_font.render('Hi-Hat', True, white)
    screen.blit(hi_hat_text, (30, 30))
    snare_text = label_font.render('Snare', True, white)
    screen.blit(snare_text, (30, 130))
    kick_text = label_font.render('Kick', True, white)
    screen.blit(kick_text, (30, 230))
    crash_text = label_font.render('Crash', True, white)
    screen.blit(crash_text, (30, 330))
    clap_text = label_font.render('Clap', True, white)
    screen.blit(clap_text, (30, 430))
    floor_text = label_font.render('Floor Tom', True, white)
    screen.blit(floor_text, (30, 530))
    for i in range(instruments-1):
        pygame.draw.line(screen, sage, (0, (i * 100) + 100), (200, (i * 100) + 100), 3)
    for i in range(beats):
        for j in range(instruments):
            if clicks[j][i] == -1:
                color = sage
            else:
                color = green
            rect = pygame.draw.rect(screen, color, 
                                [i * ((WIDTH - 200) // beats) + 200, (j * 100) +5, 
                                ((WIDTH-200) // beats) -10, ((HEIGHT-200)//instruments)-10], 0,3) # integer division
            pygame.draw.rect(screen, sage, 
                                [i * ((WIDTH - 200) // beats) + 200, (j * 100), 
                                ((WIDTH-200) // beats), ((HEIGHT-200)//instruments)], 5,5) # integer division
            pygame.draw.rect(screen, black, 
                                [i * ((WIDTH - 200) // beats) + 200, (j * 100), 
                                ((WIDTH-200) // beats), ((HEIGHT-200)//instruments)], 2,5) # integer division
            boxes.append((rect, (i, j)))
        active = pygame.draw.rect(screen, blue, [beat * ((WIDTH -200)//beats) + 200, 0, ((WIDTH-200) // beats), instruments*100], 5, 3) # draw the active beat indicator
    return boxes


while run: # runs 60 times per second
    timer.tick(fps)
    screen.fill(black)
    boxes = draw_grid(clicked, active_beat)

    if beat_changed: 
        play_notes()
        beat_changed = False


    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            for i in range(len(boxes)):
                if boxes[i][0].collidepoint(event.pos):
                    coords = boxes[i][1] # temp variable to hold the coordinates of the box that was clicked
                    clicked[coords[1]][coords[0]] *= -1 # toggle on/off by multiplying by -1
    beat_length = 3600 // bpm

    if playing:
        if active_length < beat_length:
            active_length += 1
        else:
            active_length = 0
            if active_beat < beats - 1:
                active_beat += 1
                beat_changed = True
            else:
                active_beat = 0
                beat_changed = True
            
    pygame.display.flip()
pygame.quit()


