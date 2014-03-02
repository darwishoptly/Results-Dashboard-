"""Port of JS results stats code found in bundle/results/stats.js

  The JS code is the primary authority on stats functionality. This is
  intended to be a fairly literal port so that it will be easy to
  parallel any changes on the JS end. Code that does not directly
  correspond to the JS is noted.
"""

import logging
import math


# Following 2 constants taken from bundle/results/page.js
# A variation must have at least this many visitors before counting as
# a winner or loser
_THRESHOLD_CONVERSIONS = 25
_THRESHOLD_VISITORS = 100


_Z_VALUE_FOR_ERROR_BARS = 1.95996364314087

def lzprob(z):
    """
    Returns the area under the normal curve 'to the left of' the given z value.
    Thus, 
        - for z<0, zprob(z) = 1-tail probability
        - for z>0, 1.0-zprob(z) = 1-tail probability
        - for any z, 2.0*(1.0-zprob(abs(z))) = 2-tail probability
    Adapted from z.c in Gary Perlman's |Stat.

    Usage:   lzprob(z)
    """
    Z_MAX = 6.0    # maximum meaningful z-value
    if z == 0.0:
        x = 0.0
    else:
        y = 0.5 * math.fabs(z)
        if y >= (Z_MAX*0.5):
            x = 1.0
        elif (y < 1.0):
            w = y*y
            x = ((((((((0.000124818987 * w
                        -0.001075204047) * w +0.005198775019) * w
                      -0.019198292004) * w +0.059054035642) * w
                    -0.151968751364) * w +0.319152932694) * w
                  -0.531923007300) * w +0.797884560593) * y * 2.0
        else:
            y = y - 2.0
            x = (((((((((((((-0.000045255659 * y
                             +0.000152529290) * y -0.000019538132) * y
                           -0.000676904986) * y +0.001390604284) * y
                         -0.000794620820) * y -0.002034254874) * y
                       +0.006549791214) * y -0.010557625006) * y
                     +0.011630447319) * y -0.009279453341) * y
                   +0.005353579108) * y -0.002141268741) * y
                 +0.000535310849) * y +0.999936657524
    if z > 0.0:
        prob = ((x+1.0)*0.5)
    else:
        prob = ((1.0-x)*0.5)
    return prob


def compute_stats(goals, processed_results, variations, baseline_index=0):
  """Analogous to optly.BaseStats.prototype.update

  Parameters are different because on the JS end all the data has been
  packaged up and formated. Mapping from JS to Python below:

  experiment.goals                      => goals
  experiment.results                    => processed_results
  experiment.variations                 => variations
  baselineIndex                         => baseline_index

  Returned object is same as JS end with addition of stats['rank'], a
  dict with goal ids as keys and info on winner/loser/undecided status
  of the variations as items.

  """
  (conversion_totals,
   _,
   value_totals,
   _,
   values_squared_totals,
   _,
   _,
   _,
   visitor_totals,
   _) = processed_results

  stats = {
    'average_value' : {},
    'average_value_error' : {},
    'conversion_rate' : {},
    'conversion_rate_error' : {},
    'improvement' : {},
    'min_CR_with_error' : {},
    'chance_to_beat_baseline' : {},
    'max_CR_with_error' : {},
    'min_AV_with_error' : {},
    'max_AV_with_error': {},
    'type': {},
    # rank was not in JS directly; it contains the win/loss info for
    # the different variations in a goal (similar to logic in
    # results/page.js)
    'rank': {}
  }

  if len(variations) == 0:
    # Apparently at some point it was possible for a user to delete
    # all variations... at which point calculating stats is nonsensical.
    # This logic isn't present on the results page, which as of this
    # writing doesn't even load for variation-less experiments.
    return stats

  baseline_index = max(baseline_index if baseline_index < len(variations) else 0,
                       0)
  baseline = variations[baseline_index]
  baseline_id = str(baseline['id'])
  b_visitors = visitor_totals[baseline_id]

  for goal in goals:
    goal_id = str(goal.get_id())
    stats['type'][goal_id] = _get_type_string(goal)

    stats['improvement'][goal_id] = {}
    stats['chance_to_beat_baseline'][goal_id] = {}

    # this is not from the JS original; its logic is found in
    # bundle/results/page.js (look for variationSummaryNumbers)
    variation_summary_numbers = []

    if is_revenue_goal(goal):
      stats['average_value'][goal_id] = {};
      stats['average_value_error'][goal_id] = {};
      b_value = value_totals[goal_id][baseline_id]
      b_value_squared = values_squared_totals[goal_id][baseline_id]
      b_average_value = _mean(b_visitors, b_value)
#      b_variance = _variance(b_visitors, b_value, b_value_squared)
#      b_std_dev = _sqrt(b_variance)
#      b_std_err = 0.0
#      if b_visitors > 0:
#        b_std_err = b_std_dev / _sqrt(b_visitors)
#      b_error = _Z_VALUE_FOR_ERROR_BARS * b_std_err
      min_AV_with_error = None
      max_AV_with_error = None

      for variation in variations:
        variation_id = str(variation['id'])
        is_baseline = (variation_id == baseline_id)
        value = value_totals[goal_id][variation_id]
        value_squared = values_squared_totals[goal_id][variation_id]
        visitors = visitor_totals[variation_id]

        average_value = _mean(visitors, value)
        improvement = None if is_baseline else _pct_diff(b_average_value,
                                                         average_value)
        variance = _variance(visitors, value, value_squared)
        std_dev = _sqrt(variance)
        std_err = 0
        if visitors > 0:
          std_err = std_dev / _sqrt(visitors)
        error = _Z_VALUE_FOR_ERROR_BARS * std_err
        chance_to_beat_baseline = None if is_baseline else _mean_diff_confidence(
          b_visitors, b_value, b_value_squared, visitors, value, value_squared)

        min_AV_with_error = min(min_AV_with_error, average_value - error)
        max_AV_with_error = max(max_AV_with_error, average_value + error)

        stats['average_value'][goal_id][variation_id] = average_value
        stats['average_value_error'][goal_id][variation_id] = error
        stats['improvement'][goal_id][variation_id] = improvement
        stats['chance_to_beat_baseline'][goal_id][variation_id] = \
          chance_to_beat_baseline

        # this is not from the JS original; its logic is found in
        # bundle/results/page.js (look for variationSummaryNumbers)
        variation_summary_numbers.append({
          'chance_to_beat_baseline': chance_to_beat_baseline,
          'conversion_rate': average_value,
          'conversions': value,
          'id': variation_id,
          'visitors': visitors
        })

      stats['min_AV_with_error'][goal_id] = min_AV_with_error
      stats['max_AV_with_error'][goal_id] = max_AV_with_error
    else:
      stats['conversion_rate'][goal_id] = {}
      stats['conversion_rate_error'][goal_id] = {}
      b_conversions = conversion_totals[goal_id][baseline_id]
      b_conversion_rate = _mean(b_visitors, b_conversions)
#      # sum of squares == sum of values when all values are 0 or 1
#      b_variance = _variance(b_visitors, b_conversions, b_conversions)
#      b_std_dev = _sqrt(b_variance)
#      b_std_err = 0.0
#      if b_visitors > 0:
#        b_std_err = b_std_dev / _sqrt(b_visitors)
#      b_error = _Z_VALUE_FOR_ERROR_BARS * b_std_err
      min_CR_with_error = None
      max_CR_with_error = None

      for variation in variations:
        variation_id = str(variation['id'])
        is_baseline = (variation_id == baseline_id)
        conversions = conversion_totals[goal_id][variation_id]
        visitors = visitor_totals[variation_id]

        conversion_rate = _mean(visitors, conversions)
        improvement = None if is_baseline else _pct_diff(b_conversion_rate,
                                                         conversion_rate)
        variance = _variance(visitors, conversions, conversions)
        std_dev = _sqrt(variance)
        std_err = 0.0
        if visitors > 0:
          std_err = std_dev / _sqrt(visitors)
        error = _Z_VALUE_FOR_ERROR_BARS * std_err
        chance_to_beat_baseline = None if is_baseline else _mean_diff_confidence(
          b_visitors, b_conversions, b_conversions,
          visitors, conversions, conversions)
        min_CR_with_error = min(min_CR_with_error, conversion_rate - error)
        max_CR_with_error = max(max_CR_with_error, conversion_rate + error)

        stats['conversion_rate'][goal_id][variation_id] = conversion_rate
        stats['improvement'][goal_id][variation_id] = improvement
        stats['conversion_rate_error'][goal_id][variation_id] = error
        stats['chance_to_beat_baseline'][goal_id][variation_id] = \
          chance_to_beat_baseline

        # this is not from the JS original; its logic is found in
        # bundle/results/page.js (look for variationSummaryNumbers)
        variation_summary_numbers.append({
          'chance_to_beat_baseline': chance_to_beat_baseline,
          'conversion_rate': conversion_rate,
          'conversions': conversions,
          'id': variation_id,
          'visitors': visitors
        })

      stats['min_CR_with_error'][goal_id] = min_CR_with_error
      stats['max_CR_with_error'][goal_id] = max_CR_with_error

    stats['rank'][goal_id] = _summarize(variation_summary_numbers)

  return stats


def _summarize(variation_data):
  """Analogous to optly.BaseStats.prototype.summarize

  Returned object contains different info, see comments below.

  """
  winners = []
  losers = []
  undecideds = []

  for variation_numbers in variation_data:
    # skip baseline
    if variation_numbers['chance_to_beat_baseline'] is None:
      continue

    if (variation_numbers['visitors'] >= _THRESHOLD_VISITORS and
        variation_numbers['conversions'] >= _THRESHOLD_CONVERSIONS and
        variation_numbers['chance_to_beat_baseline'] >= 0.95):
      winners.append(variation_numbers)
    elif (variation_numbers['visitors'] >= _THRESHOLD_VISITORS and
          variation_numbers['conversions'] >= _THRESHOLD_CONVERSIONS and
          variation_numbers['chance_to_beat_baseline'] <= 0.05):
      losers.append(variation_numbers)
    else:
      undecideds.append(variation_numbers)

  def compare_conversion_rate(a, b):
    return cmp((b['conversion_rate'] or 0) - (a['conversion_rate'] or 0), 0)
  winners.sort(compare_conversion_rate)
  losers.sort(compare_conversion_rate)
  undecideds.sort(compare_conversion_rate)

  # This is different from the JS original: instead having each variation
  # being represented by some of its data, we only record the variation id,
  # since the other stats are already known. (The JS has some data
  # redundancy b/c the code is split.)
  return {
    'winners': [winner['id'] for winner in winners],
    'losers': [loser['id'] for loser in losers],
    'undecideds': [undecided['id'] for undecided in undecideds]
  }


def _get_type_string(goal):
  if isinstance(goal, project_goals.ProjectGoal):
    return project_goals.TYPE_TO_STRING[goal.goal_type]

  # for DashboardGoals (which are deprecated)
  return goal.get_type_string()


def _mean(visitors, sum_of_values):
  #In the JS code, sumOfValues is sometimes null, in which case
  #division causes it to behave like 0.
  #The equivalent idea here is that sum_of_values may be
  #None, in which case the function behaves as if it's 0.
  if sum_of_values is None:
    sum_of_values = 0

  return 0 if visitors <= 0 else (float(sum_of_values) / visitors)


def _mean_diff_confidence(b_visitors,
                          b_value,
                          b_value_squared,
                          visitors,
                          value,
                          value_squared,
                          lower_bound=0,
                          absolute_value=False):

  b_mean = _mean(b_visitors, b_value)
  # print "B Mean ", b_mean
  b_actual_mean = b_value / b_visitors
  # print "B Actual Mean " , b_actual_mean

  b_variance = _variance(b_visitors, b_value, b_value_squared)
  # print "B Variance ", b_variance

  mean = _mean(visitors, value)
  # print "Mean ", mean
  variance = _variance(visitors, value, value_squared)
  # print "Variance ", variance

  mean_diff = mean - b_mean
  mean_diff_variance = _mean_diff_variance(
    b_visitors, b_variance, visitors, variance)

  # print "Mean Diff Variance " , mean_diff_variance

  # The following two lines are different from the JS, which has NaN.
  if mean_diff_variance is None:
    return None

  mean_diff_std_dev = _sqrt(mean_diff_variance)

  # print "Mean Diff Std Dev " , mean_diff_std_dev

  if mean_diff_std_dev == 0:
    return 0

  normed_diff = float(mean_diff - lower_bound) / mean_diff_std_dev
  # print "Normed_diff " , normed_diff
  # print "Mean_diff ", mean_diff

  #if mean_diff < 0:
  #  normed_diff *= -1
 
  # print "Z from stats.py package ", lzprob(normed_diff)

  return _normal_p(normed_diff)


def _mean_diff_variance(b_visitors, b_variance, visitors, variance):
  if b_visitors == 0 or b_variance == "N/A" or visitors == 0 or variance == "N/A":
    # note that "N/A" from the JS has been swapped with None
    return None

  # next 4 lines are added to mimic the type coercion that happens in JS
  # when dividing null
  if b_variance is None:
    b_variance = 0
  if variance is None:
    variance = 0

  if b_visitors in [None, 0] or visitors in [None, 0]:
    if 0 in [b_variance, variance]:
      # in JS, 0/0 & 0/null yield NaN
      return None

    # mimic JS behavior where division by 0 yields infinity
    return float("Inf")

  return (float(b_variance) / b_visitors) + (float(variance) / visitors)


def _normal_p(x):
  """Taken from stats.js in bundle_relaxed.
  Approximation, see http://people.math.sfu.ca/~cbm/aands/page_932.htm
  Comment from JS:
  Abramowitz & Stegun 26.2.19
  
  """
  d1 = 0.0498673470
  d2 = 0.0211410061
  d3 = 0.0032776263
  d4 = 0.0000380036
  d5 = 0.0000488906
  d6 = 0.0000053830

  a = abs(x);
  t = 1.0 + a*(d1+a*(d2+a*(d3+a*(d4+a*(d5+a*d6)))))

  # to 16th power
  t = math.pow(t, 16)
  t = 1.0 / (t+t);  # the MINUS 16th

  if (x >= 0):
    t = 1 - t

  return t;


def _pct_diff(baseline, comparison):
  return 0 if baseline == 0 else (float(comparison - baseline) / baseline)


def _sqrt(number):
  """Square root that more closely resembles Math.sqrt() in JS."""
  if not number:
    number = 0

  result = None
  try:
    result = math.sqrt(float(number))
  except ValueError:
    # Handling of square root for negative numbers isn't consistent (e.g.
    # in GAE production, an exception is thrown whereas locally nan is
    # returned). Here we cover the case on GAE.
    # Why does this ever even happen? One case is the 'anonymous
    # conversion' stuff (which is used at least by ebay),
    # in which the # conversions may be greater than the # visitors. In
    # that case, computing variance (our variance function is currently
    # written with limiting assumptions) involves the square root of a
    # negative number.
    if number < 0:
      return float("nan")
  except:
    logging.warning("Can't take square root of %s" % number)
    pass

  return result


def _variance(visitors, sum_of_values, sum_of_squares):

  adjusted_mean_of_squares = _mean(visitors - 1, sum_of_squares)
  mean = _mean(visitors, sum_of_values)
  mean_squared = mean * mean
  mean_squared_coeff = float(visitors) / (visitors - 1)

  return adjusted_mean_of_squares - (mean_squared * mean_squared_coeff)

def pVal(visitors, value, value_squared, b_visitors, b_value, b_value_squared):
# visitors = 2357
# value = 29134370
# value_squared = 1301159820303
# b_visitors = 2328
# b_value = 31775214
# b_value_squared = 1414298616412


# visitors = 13091
# value = 8123290
# value_squared = 2830369340044
# b_visitors = 13268
# b_value = 6627666
# b_value_squared = 891475072298
# 
# 
# # 296378765 - Category Landing Page - Revenue
# 
# #VARIATION
# visitors = 94389
# value = 22732319
# value_squared = 1844114321446
# 
# # ORIGINAL
# b_visitors = 123735
# b_value = 28148167
# b_value_squared = 4319999227537
# 
# # 296378765 - Category Landing Page - Engagement
# 
# #VARIATION
# visitors = 94389
# value = 70845
# value_squared = 70845
# 
# # ORIGINAL
# b_visitors = 123735
# b_value = 93087
# b_value_squared = 93087





 new_mean_diff_confidence = _mean_diff_confidence(
       visitors, value, value_squared, b_visitors, b_value, b_value_squared)

 variance = _variance(visitors, value, value_squared)
 std_dev = _sqrt(variance)
 b_variance = _variance(b_visitors, b_value, b_value_squared)
 b_std_dev = _sqrt(b_variance)
 
 # print new_mean_diff_confidence
 return new_mean_diff_confidence 
	
# print "Variance: " , variance
# print "B Variance: " , b_variance
# print "std dev: " , std_dev
# print "B Std Dev: " , b_std_dev
# print "Chance to beat the baseline: " , new_mean_diff_confidence