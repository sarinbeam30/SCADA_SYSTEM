from kalman import SingleStateKalmanFilter
from moving_average import MovingAverageFilter
import statistics

test1 = [-70,-70,-72,-75,-70,-72,-78,-82,-72,-74,-70,-65,-70,-74,-71,-69,-70,-74,-71,-74]
ma5_filter_estimates = []
ma10_filter_estimates = []
kalman_filter_estimates = []
ma5_filter = MovingAverageFilter(5)
ma10_filter = MovingAverageFilter(5)

A = 1  # No process innovation
C = 1  # Measurement
B = 0  # No control input
Q = 0.03 # Process covariance
R = 1  # Measurement covariance
x = 65  # Initial estimate
P = 2  # Initial covariance

kalman_filter = SingleStateKalmanFilter(A, B, C, x, P, Q, R)

for i in test1:
  ma5_filter.step(i)
  ma5_filter_estimates.append(ma5_filter.current_state())

  ma10_filter.step(i)
  ma10_filter_estimates.append(ma10_filter.current_state())

  kalman_filter.step(0, i)
  kalman_filter_estimates.append(kalman_filter.current_state())

mean = statistics.mean(test1)
mode = max(test1)
print(mean)
print(mode)
print(ma5_filter_estimates)
print(ma10_filter_estimates)
print(kalman_filter_estimates)