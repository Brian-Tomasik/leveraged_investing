import numpy
import util
import operator
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
        pyplot.xlabel("Real present value of donated $")
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
    pyplot.ylabel("Real present value of donated $")
    pyplot.savefig(outfilepath + "_wealthtraj")
    pyplot.close()

def graph_carried_taxes_trajectories(carried_tax_histories, outfilepath):
    num_days = len(carried_tax_histories[0])
    x_axis = [float(day)/DAYS_PER_YEAR for day in range(num_days)]

    # Plot individual trajectories
    for individual in carried_tax_histories:
        assert len(individual) == num_days, "Inconsistent number of days in history vectors"
        pyplot.plot(x_axis, individual)
    pyplot.title("Carried capital gains/losses vs. year of simulation")
    pyplot.xlabel("Years since beginning")
    pyplot.ylabel("Carried short+long-term taxes ($)")
    pyplot.savefig(outfilepath + "_carrtax")
    pyplot.close()

def graph_trends_vs_leverage_amount(output_queue, outdir_name):
    # Sort the queue by the N leverage value
    output_tuples = []
    while not output_queue.empty():
        output_tuples.append(output_queue.get())
    output_tuples.sort(key=operator.itemgetter(0))

    # Get the axes
    attributes = dict()
    KEYS = ["Ns", "(Mean wealth margin)/(Mean wealth regular)", 
            "Error in means ratio", "(Median wealth margin)/(Median wealth regular)", 
            "(Expected utility margin)/(Expected utility regular)", 
            "Error in exp-util ratio"]
    for key in KEYS:
        attributes[key] = []
    for tuple in output_tuples:
        assert len(KEYS) == len(tuple), "Tuple is wrong length"
        for i in range(len(tuple)):
            attributes[KEYS[i]].append(tuple[i])

    # Plot the axes
    x_axis = attributes["Ns"]
    fig,(ax1)=pyplot.subplots(1,1)

    key = "(Mean wealth margin)/(Mean wealth regular)"
    y_axis = attributes[key]
    yerr = attributes["Error in means ratio"]
    ax1.errorbar(x_axis, y_axis, yerr=yerr, label=key)
    min_y = min(y_axis)

    key = "(Median wealth margin)/(Median wealth regular)"
    y_axis = attributes[key]
    ax1.plot(x_axis, y_axis, label=key)
    min_y = min(min_y, min(y_axis))
    max_med_or_EU = max(y_axis)

    key = "(Expected utility margin)/(Expected utility regular)"
    y_axis = attributes[key]
    yerr = attributes["Error in exp-util ratio"]
    ax1.errorbar(x_axis, y_axis, yerr=yerr, label=key)
    min_y = min(min_y, min(y_axis))
    max_med_or_EU = max(max_med_or_EU, max(y_axis))

    # Set axes
    pyplot.axis([min(x_axis)-.1, max(x_axis)+.1, 0, max_med_or_EU+1])

    """
    THIS DOESN'T SEEM TO WORK...
    # Here's logic to remove error bars from the legend.... 
    # http://stackoverflow.com/questions/14297714/matplotlib-dont-show-errorbars-in-legend
    # get handles
    handles, labels = ax1.get_legend_handles_labels()
    # remove the errorbars
    handles = [h[0] for h in handles] # GIVES AN EXCEPTION: 'Line2D' object does not support indexing
    # use them in the legend
    ax1.legend(handles, labels)
    """
    
    pyplot.title("Margin performance vs. amount of leverage")
    pyplot.xlabel("Amount of leverage (e.g., 2 means 2X leverage)")
    pyplot.ylabel("Ratios of margin account's value over regular account's value")
    pyplot.legend()
    pyplot.savefig("{}\{}".format(outdir_name,"graph"))
    pyplot.close()