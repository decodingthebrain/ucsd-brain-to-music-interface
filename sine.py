import pygame
import math
import random as rand
pygame.init()

screen = pygame.display.set_mode((1000,500))

while True:
    for events in pygame.event.get():
        if events.type == pygame.QUIT:
            pygame.quit()
            quit()
    t = pygame.time.get_ticks() / 4 % 1000 # 3 is speed, 1000 is width
   
    x = t
    y = math.sin(t/50) * (rand.randint(10, 100)) + 200# 50 is frequency, 100 is amplitude, 200 is vertical shift
    # have background be pink
    # leave a trail behind the ball
    
    pygame.draw.circle(screen, 'red', (x, y), 1)
    

    x_cos = t
    y_cos = math.cos(t/25) *  (rand.randint(10, 100)) +400
    pygame.draw.circle(screen, 'blue', (x_cos, y_cos), 1)


    
    pygame.display.update()

        