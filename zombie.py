from pico2d import *

import random
import math
import game_framework
import game_world
from behavior_tree import BehaviorTree, Action, Sequence, Condition, Selector
import play_mode


# zombie Run Speed
PIXEL_PER_METER = (10.0 / 0.3)  # 10 pixel 30 cm
RUN_SPEED_KMPH = 20.0  # Km / Hour
RUN_SPEED_MPM = (RUN_SPEED_KMPH * 1000.0 / 60.0)
RUN_SPEED_MPS = (RUN_SPEED_MPM / 60.0)
RUN_SPEED_PPS = (RUN_SPEED_MPS * PIXEL_PER_METER)

# zombie Action Speed
TIME_PER_ACTION = 0.5
ACTION_PER_TIME = 1.0 / TIME_PER_ACTION
FRAMES_PER_ACTION = 10.0

animation_names = ['Walk', 'Idle']


class Zombie:
    images = None

    def load_images(self):
        if Zombie.images == None:
            Zombie.images = {}
            for name in animation_names:
                Zombie.images[name] = [load_image("./zombie/" + name + " (%d)" % i + ".png") for i in range(1, 11)]
            Zombie.font = load_font('ENCR10B.TTF', 40)
            Zombie.marker_image = load_image('hand_arrow.png')


    def __init__(self, x=None, y=None):
        self.x = x if x else random.randint(100, 1180)
        self.y = y if y else random.randint(100, 924)
        self.load_images()
        self.dir = 0.0      # radian 값으로 방향을 표시
        self.speed = 0.0
        self.frame = random.randint(0, 9)
        self.state = 'Idle'
        self.ball_count = 0
        self.tx, self.ty = 0,0

        self.build_behavior_tree()

        self.patrol_locations = [(43, 274), (1118, 274), (1050, 494), (575, 804), (235, 991),
                                 (575, 804), (1050, 494), (1118, 274)]
        self.loc_no = 0


    def get_bb(self):
        return self.x - 50, self.y - 50, self.x + 50, self.y + 50


    def update(self):
        self.frame = (self.frame + FRAMES_PER_ACTION * ACTION_PER_TIME * game_framework.frame_time) % FRAMES_PER_ACTION
        # fill here
        self.bt.run()

    def draw(self):
        Zombie.marker_image.draw(self.tx, self.ty)
        if math.cos(self.dir) < 0:
            Zombie.images[self.state][int(self.frame)].composite_draw(0, 'h', self.x, self.y, 100, 100)
        else:
            Zombie.images[self.state][int(self.frame)].draw(self.x, self.y, 100, 100)
        self.font.draw(self.x - 10, self.y + 60, f'{self.ball_count}', (0, 0, 255))
        draw_rectangle(*self.get_bb())

    def handle_event(self, event):
        pass

    def handle_collision(self, group, other):
        if group == 'zombie:ball':
            self.ball_count += 1


    def set_target_location(self, x=None, y=None):
        if not x or not y:
            raise ValueError('Location should be given')
        self.tx, self.ty = x, y
        return BehaviorTree.SUCCESS

    def distance_less_than(self, x1, y1, x2, y2, r):
        distance2 = (x1-x2)**2 + (y1-y2)**2 # sqrt 구하는 데 시간이 많이 걸리니까, 거리 비교만 할 때는 루트 x
        return distance2 < (PIXEL_PER_METER * r)**2


    def move_slightly_to(self, tx, ty): # 목적지까지 프레임타임 단위로(프레임마다) 살짝씩 가는 함수
        self.dir = math.atan2(ty-self.y, tx-self.x) # dir을 radian으로 해석
        distance = RUN_SPEED_PPS * game_framework.frame_time
        self.x += distance * math.cos(self.dir)
        self.y += distance * math.sin(self.dir)

    def move_to(self, r=0.5):
        self.state = 'Walk'
        self.move_slightly_to(self.tx, self.ty)
        if self.distance_less_than(self.tx, self.ty, self.x, self.y, r):
            return BehaviorTree.SUCCESS
        else:
            return BehaviorTree.RUNNING

    def set_random_location(self):
        self.tx, self.ty = random.randint(100, 1280-100), random.randint(100, 1024-100)
        return BehaviorTree.SUCCESS

    def is_boy_nearby(self, distance): # Condition Node
        if self.distance_less_than(play_mode.boy.x, play_mode.boy.y, self.x, self.y, distance):
            return BehaviorTree.SUCCESS
        else:
            return BehaviorTree.FAIL

    def move_to_boy(self, r=0.5):
        self.state = 'Walk'
        self.move_slightly_to(play_mode.boy.x, play_mode.boy.y)
        if self.distance_less_than(play_mode.boy.x, play_mode.boy.y, self.x, self.y, r):
            return BehaviorTree.SUCCESS
        else:
            return BehaviorTree.RUNNING

    def get_patrol_location(self):
        self.tx, self.ty = self.patrol_locations[self.loc_no]
        self.loc_no = (self.loc_no + 1) % len(self.patrol_locations)
        return BehaviorTree.SUCCESS

    def run_away_from_boy(self):
        self.state = 'Walk'
        dx = self.x - play_mode.boy.x
        dy = self.y - play_mode.boy.y
        distance = math.sqrt(dx**2 + dy**2)

        ndx = dx/distance
        ndy = dy/distance
        self.tx = self.x + ndx*PIXEL_PER_METER*8
        self.ty = self.y + ndy*PIXEL_PER_METER*8

        self.move_slightly_to(self.tx, self.ty)

        if self.distance_less_than(play_mode.boy.x, play_mode.boy.y, self.x, self.y, 7):
            return BehaviorTree.RUNNING # RUNNING과 FAIL의 차이
        else:
            return BehaviorTree.SUCCESS
        # self.set_target_location(self.x - bx+100, self.y - by+100)
        # self.move_to() --> ??

    def is_zombie_ball_more(self):
        if self.ball_count >= play_mode.boy.ball_count:
            return BehaviorTree.SUCCESS
        else:
            return BehaviorTree.FAIL

    def is_boy_ball_more(self):
        if self.ball_count < play_mode.boy.ball_count:
            return BehaviorTree.SUCCESS
        else:
            return BehaviorTree.FAIL

    def build_behavior_tree(self):
        a1 = Action('Set target location', self.set_target_location, 1000, 1000)
        a2 = Action('Move to', self.move_to)
        move_to_target_location = Sequence('Move to target location', a1, a2)

        a3 = Action('Set random location', self.set_random_location)
        wander = Sequence('Wander', a3, a2)

        c1 = Condition('소년이 근처에 있는가?', self.is_boy_nearby, 7)
        a4 = Action('소년한테 접근', self.move_to_boy)
        chase_boy = Sequence('소년을 추적', c1, a4)

        chase_or_flee = Selector('추적 또는 배회',chase_boy, wander)

        a5 = Action('Set patrol location', self.get_patrol_location)
        patrol = Sequence('좀비 정찰', a5, a2)
        chase_or_patrol = Selector('추적 또는 정찰', chase_boy, patrol)

        a6 = Action('소년에게서 도망!', self.run_away_from_boy)
        c2 = Condition('좀비 공이 더 많다!', self.is_zombie_ball_more)
        c3 = Condition('소년 공이 더 많다!', self.is_boy_ball_more)

        chase_boy2 = Sequence('소년 추적', c2, a4)
        run_away_zombie2 = Sequence('좀비 도망', c3, a6)
        chase_or_run_away = Selector('추적 또는 도망', chase_boy2, run_away_zombie2)
        detect_boy = Sequence('소년 탐지', c1, chase_or_run_away)


        root = Selector('소년 탐지 또는 배회', detect_boy, wander)

        self.bt = BehaviorTree(root)
