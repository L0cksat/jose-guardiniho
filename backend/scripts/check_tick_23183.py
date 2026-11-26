from app.telemetry.models import MatchFrame, PlayerFrame
from app.tactics.rules import count_home_flanks, short_flank, count_press, press_warning

ys = [
    27.88177, -7.565001, -2.0313807, -2.0146089, -27.16998,
    -23.115896, -32.34505, -26.522415, -12.115001, -11.465,
    -31.306904, -12.548943, -20.41734, -29.62739,
]

xs = [
    8.544486, -39.25, -3.8333228, 11.195223, 13.810543,
    14.012387, 7.7371507, -3.6186125, -39.25, -39.25,
    -3.096166, -19.537403, 22.112944, -9.109275,
]

away_xs = [
    1.486399, 20.94654, 7.1638894, -2.1013513, -39.25,
    -0.95162845, -39.25, -39.25, 9.6609, 4.284797,
    -39.25, 10.562162, 9.883649, -12.556592,
]
away_ys = [
    -47.881252, -23.84156, -32.674747, -31.541027, 7.565001,
    -30.02478, 10.165001, 8.865001, -8.163684, -9.800307,
    9.515001, -30.69639, -25.068752, -19.99992,
]

frame = MatchFrame(
    match_id = "match-1795519768911",
    sequence=107476,
    tick=23183,
    display_tick=22366,
    period=2,
    captured_unix_milliseconds=1795522617438,
    ball_x_centimeters=1402,
    ball_y_centimeters=-2366,
    players=[PlayerFrame(player_id=i, team="home", y=y, x=x,) for i, (x,y) in enumerate(zip(xs, ys))] + [PlayerFrame(player_id=i, team="away", y=y, x=x,) for i, (x,y) in enumerate(zip(away_xs, away_ys))],

)

print(count_home_flanks(frame))
print(short_flank(frame))
print(count_press(frame))
print(press_warning(frame, user_team="home"))
