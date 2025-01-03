library(ggplot2)
library(tidyverse)
library(gridExtra)

# Parameters
n_stations = 40
short_line_start = 10
short_line_end = 30
simulation_runs = 20
time_offset_before = 3  # minutes
time_offset_after = 1   # minutes
arrival_rate = 0.3      # proportion of passengers arriving per minute

# Generate passenger patterns
generate_passenger_patterns = function() {
  boarding_mean = 15
  boarding_sd = 5
  boarding_pattern = dnorm(1:n_stations, mean=boarding_mean, sd=boarding_sd)
  boarding_pattern = boarding_pattern / max(boarding_pattern) * 100
  
  alighting_mean = 23
  alighting_sd = 3
  alighting_pattern = dnorm(1:n_stations, mean=alighting_mean, sd=alighting_sd)
  alighting_pattern = alighting_pattern / max(alighting_pattern) * 100
  
  return(list(boarding=boarding_pattern, alighting=alighting_pattern))
}

# Modified simulation with continuous passenger arrivals
simulate_trains = function(patterns, timing) {
  long_train = numeric(n_stations)
  short_train = numeric(n_stations)
  long_load = 0
  short_load = 0
  
  total_boarded = 0
  total_alighted = 0
  
  for(i in 1:n_stations) {
    new_passengers = round(patterns$boarding[i])
    total_boarded = total_boarded + new_passengers
    
    if(i >= short_line_start && i <= short_line_end) {
      if(timing == "before") {
        # Short train arrives first
        short_boarding = new_passengers
        long_boarding = round(arrival_rate * time_offset_before * patterns$boarding[i])
      } else if(timing == "after") {
        # Long train arrives first
        long_boarding = new_passengers
        short_boarding = round(arrival_rate * time_offset_after * patterns$boarding[i])
      } else {
        # Trains arrive together
        short_boarding = round(new_passengers * 0.5)
        long_boarding = new_passengers - short_boarding
      }
      
      # Process short train
      short_alighting = round(short_load * (patterns$alighting[i] / 100))
      total_alighted = total_alighted + short_alighting
      short_load = short_load + short_boarding - short_alighting
      short_train[i] = short_load
    } else {
      # Outside short line range
      long_boarding = new_passengers
    }
    
    # Process long train
    long_alighting = round(long_load * (patterns$alighting[i] / 100))
    total_alighted = total_alighted + long_alighting
    long_load = long_load + long_boarding - long_alighting
    long_train[i] = long_load
  }
  
  return(list(
    long = long_train,
    short = short_train,
    total_boarded = total_boarded,
    total_alighted = total_alighted,
    final_load = long_load + short_load
  ))
}

# Run simulations
patterns = generate_passenger_patterns()
results_before = simulate_trains(patterns, "before")
results_after = simulate_trains(patterns, "after")
results_same = simulate_trains(patterns, "same")

# Create load plots with total passengers
create_load_plot = function(results, title) {
  df = data.frame(
    station = 1:n_stations,
    long_train = results$long,
    short_train = results$short,
    total_load = results$long + results$short
  )
  
  ggplot(df) +
    geom_line(aes(x=station, y=long_train, color="Long Line")) +
    geom_line(aes(x=station, y=short_train, color="Short Line")) +
    geom_line(aes(x=station, y=total_load, color="Total Load"), linetype="dashed") +
    geom_vline(xintercept=c(short_line_start, short_line_end), 
               linetype="dotted", color="gray") +
    scale_color_manual(values=c("Long Line"="blue", 
                                "Short Line"="red",
                                "Total Load"="purple")) +
    labs(title=title,
         x="Station Number",
         y="Number of Passengers") +
    theme_minimal()
}

# Create comparison plot of total loads
total_loads = data.frame(
  station = rep(1:n_stations, 3),
  scenario = factor(rep(c("Before", "After", "Same"), each=n_stations)),
  total_load = c(results_before$long + results_before$short,
                 results_after$long + results_after$short,
                 results_same$long + results_same$short)
)

p_total_comparison = ggplot(total_loads) +
  geom_line(aes(x=station, y=total_load, color=scenario)) +
  geom_vline(xintercept=c(short_line_start, short_line_end), 
             linetype="dotted", color="gray") +
  labs(title="Total Load Comparison Across Scenarios",
       x="Station Number",
       y="Total Passengers") +
  theme_minimal()

# Arrange plots
grid.arrange(
  create_load_plot(results_before, "Short Train Before (3 min)"),
  create_load_plot(results_after, "Short Train After (1 min)"),
  create_load_plot(results_same, "Same Time"),
  p_total_comparison,
  ncol=1
)

# Print metrics
metrics = data.frame(
  Scenario = c("Before", "After", "Same"),
  Max_Short_Load = c(max(results_before$short), 
                     max(results_after$short), 
                     max(results_same$short)),
  Max_Long_Load = c(max(results_before$long),
                    max(results_after$long),
                    max(results_same$long)),
  Max_Total_Load = c(max(results_before$long + results_before$short),
                     max(results_after$long + results_after$short),
                     max(results_same$long + results_same$short))
)

print("Load Metrics:")
print(metrics)