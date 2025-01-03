# Modified simulation with continuous offsets
simulate_trains = function(patterns, timing, custom_offsets = NULL) {
  long_train = numeric(n_stations)
  short_train = numeric(n_stations)
  long_load = 0
  short_load = 0
  
  total_boarded = 0
  total_alighted = 0
  
  time_offset_before = ifelse(is.null(custom_offsets), time_offset_before, custom_offsets[1])
  time_offset_after = ifelse(is.null(custom_offsets), time_offset_after, custom_offsets[2])
  
  for(i in 1:n_stations) {
    new_passengers = patterns$boarding[i]
    total_boarded = total_boarded + new_passengers
    
    if(i >= short_line_start && i <= short_line_end) {
      if(timing == "before") {
        short_boarding = new_passengers
        long_boarding = arrival_rate * time_offset_before * patterns$boarding[i]
      } else if(timing == "after") {
        long_boarding = new_passengers
        short_boarding = arrival_rate * time_offset_after * patterns$boarding[i]
      } else if(timing == "custom") {
        short_boarding = new_passengers / (1 + time_offset_after / time_offset_before)
        long_boarding = new_passengers - short_boarding
      } else {
        short_boarding = new_passengers * 0.5
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

# Optimization function
find_optimal_offsets = function() {
  objective = function(offsets) {
    results = simulate_trains(patterns, "custom", custom_offsets = offsets)
    max_short = max(results$short)
    max_long = max(results$long)
    abs(max_short - max_long)
  }
  
  initial_offsets = c(3, 1)
  opt = optim(
    par = initial_offsets,
    fn = objective,
    method = "L-BFGS-B",
    lower = c(0, 0),
    upper = c(10, 10)
  )
  return(opt$par)
}

# Run optimization
optimal_offsets = find_optimal_offsets()
time_offset_before = optimal_offsets[1]
time_offset_after = optimal_offsets[2]

cat("Optimal time offsets:\n")
cat("  Time Offset Before:", time_offset_before, "minutes\n")
cat("  Time Offset After:", time_offset_after, "minutes\n")

# Validate with optimized offsets
results_optimized = simulate_trains(patterns, "custom", custom_offsets = optimal_offsets)

# Create optimized load plot
p_optimized = create_load_plot(results_optimized, "Optimized Offsets")

# Display metrics
metrics_optimized = data.frame(
  Scenario = "Optimized",
  Max_Short_Load = max(results_optimized$short),
  Max_Long_Load = max(results_optimized$long),
  Max_Total_Load = max(results_optimized$long + results_optimized$short)
)

print("Optimized Load Metrics:")
print(metrics_optimized)

# Display plots including the optimized scenario
grid.arrange(
  create_load_plot(results_before, "Short Train Before (3 min)"),
  create_load_plot(results_after, "Short Train After (1 min)"),
  create_load_plot(results_same, "Same Time"),
  p_optimized,
  p_total_comparison,
  ncol=1
)
