import simulator.main as main
import math
def update_steering(left_pressed, right_pressed, dt):

    if left_pressed:
        main.steering_angle -= main.STEER_RATE * dt

    elif right_pressed:
        main.steering_angle += main.STEER_RATE * dt

    else:
        # Return steering towards center
        if main.steering_angle > 0:
            main.steering_angle = max(0, main.steering_angle - main.CENTER_RATE * dt)
        elif main.steering_angle < 0:
            main.steering_angle = min(0, main.steering_angle + main.CENTER_RATE * dt)

    main.steering_angle = max(-main.MAX_STEERING,
                         min(main.MAX_STEERING, main.steering_angle))
    
def calculate_lateral_accel():
    speed = main.current_speed / 3.6  # m/s

    if abs(main.steering_angle) < 1e-4 or speed < 1:
        return 0.0
    
    turn_radius = main.WHEELBASE / math.tan(main.steering_angle)

    main.lateral_accel = speed * speed / turn_radius