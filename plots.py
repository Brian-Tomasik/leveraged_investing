import numpy
import util
from matplotlib import pyplot

DAYS_PER_YEAR = 365

def graph_results(account_values, num_samples, outfilepath):
    alpha_for_pyplot = .5
    num_bins = max(10, num_samples/10)
    for type in ["regular", "margin", "matched401k"]:
        median_value = util.percentile(account_values[type], .5)
        numpy_array = numpy.array(account_values[type])
        bin_min = min(numpy_array)
        bin_max = 4 * median_value # avoids having a distorted graph due to far-right skewed values
        graph_bins = numpy.linspace(bin_min, bin_max, num_bins)
        pyplot.hist(numpy_array, bins=graph_bins, alpha=alpha_for_pyplot, color="r")
        pyplot.title("Distribution of results for " + type + " investing")
        pyplot.xlabel("Present value of savings ($)")
        pyplot.ylabel("Frequency out of " + str(num_samples) + " runs")
        pyplot.savefig(outfilepath + "_hist_" + type)
        pyplot.close()

def graph_historical_margin_to_assets_ratios(collection_of_ratios, avg_ratios, outfilepath):
    num_days = len(avg_ratios)
    x_axis = [float(day)/DAYS_PER_YEAR for day in range(num_days)]

    # Plot individual trajectories
    for individual in collection_of_ratios:
        assert len(individual) == num_days, "Inconsistent number of days in history vectors"
        pyplot.plot(x_axis, individual)
    pyplot.title("Individual trajectories of margin-to-assets ratios vs. year of simulation")
    pyplot.xlabel("Years since beginning")
    pyplot.ylabel("Margin-to-assets ratio")
    pyplot.savefig(outfilepath + "_indMTA")
    pyplot.close()

    # Plot average trajectory
    pyplot.plot(x_axis, avg_ratios)
    pyplot.title("Average trajectory of margin-to-assets ratios vs. year of simulation")
    pyplot.xlabel("Years since beginning")
    pyplot.ylabel("Average margin-to-assets ratio")
    pyplot.savefig(outfilepath + "_avgMTA")
    pyplot.close()

def graph_historical_wealth_trajectories(wealth_histories, outfilepath):
    num_days = len(wealth_histories[0])
    x_axis = [float(day)/DAYS_PER_YEAR for day in range(num_days)]

    # Plot individual trajectories
    for individual in wealth_histories:
        assert len(individual) == num_days, "Inconsistent number of days in history vectors"
        pyplot.plot(x_axis, individual)
    pyplot.title("Wealth trajectories vs. year of simulation")
    pyplot.xlabel("Years since beginning")
    pyplot.ylabel("Wealth ($)")
    pyplot.savefig(outfilepath + "_wealthtraj")
    pyplot.close()