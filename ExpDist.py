"""Port of JS results stats code found in bundle/results/stats.js

  The JS code is the primary authority on stats functionality. This is
  intended to be a fairly literal port so that it will be easy to
  parallel any changes on the JS end. Code that does not directly
  correspond to the JS is noted.
"""

import logging
import math

# from helpers.goal import is_revenue_goal
# from models import project_goals

# Following 2 constants taken from bundle/results/page.js
# A variation must have at least this many visitors before counting as
# a winner or loser
_THRESHOLD_CONVERSIONS = 25
_THRESHOLD_VISITORS = 100


_Z_VALUE_FOR_ERROR_BARS = 1.95996364314087

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
        chance_to_beat_baseline = None if is_baseline else _revenue_p_value(
          b_visitors, b_value, visitors, value)

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
  if b_value_squared in [0, None, ""]:
    b_value_squared = b_value
  if value_squared in [0, None, ""]:
    value_squared = value

  b_mean = _mean(b_visitors, b_value)
  b_variance = _variance(b_visitors, b_value, b_value_squared)
  mean = _mean(visitors, value)
  variance = _variance(visitors, value, value_squared)
  mean_diff = mean - b_mean
  mean_diff_variance = _mean_diff_variance(
    b_visitors, b_variance, visitors, variance)

  # The following two lines are different from the JS, which has NaN.
  if mean_diff_variance is None:
    return None

  mean_diff_std_dev = _sqrt(mean_diff_variance)

  if mean_diff_std_dev == 0:
    return 0

  normed_diff = float(mean_diff - lower_bound) / mean_diff_std_dev
  if mean_diff < 0 and absolute_value:
    normed_diff *= -1

  return _normal_p(normed_diff)


def _revenue_p_value(bVisitors, bValue, visitors, value):
  """ Uses an FTest to calculate a p-value for revenue experiments, assuming
  and exponential distribution

  Implentation lifted from http://www.math.ucla.edu/~tom/distributions/Fcdf.html
  which in tern appears lifted from a numerical methods book based on the style.

  Tested against 'pf' in R
  """

  def log_gamma(Z):
    S = 1 + 76.18009173 / Z - 86.50532033 / (Z + 1) + 24.01409822 / (Z + 2) - \
      1.231739516 / (Z + 3) + .00120858003 / (Z + 4) - .00000536382 / (Z + 5)
    LG = (Z - .5) * math.log(Z + 4.5) - (Z + 4.5) + math.log(S * 2.50662827465)
    return LG
  

  def beta_inc(X, A, B):
    A0 = 0
    B0 = 1
    A1 = 1
    B1 = 1
    M9 = 0
    A2 = 0
    C9 = 0
    while (abs((A1 - A2) / A1) > .00001):
      A2 = A1
      C9 = -(A + M9) * (A + B + M9) * X / (A + 2 * M9) / (A + 2 * M9 + 1)
      A0 = A1 + C9 * A0
      B0 = B1 + C9 * B0
      M9 = M9 + 1
      C9 = M9 * (B - M9) * X / (A + 2 * M9 - 1) / (A + 2 * M9)
      A1 = A0 + C9 * A1
      B1 = B0 + C9 * B1
      A0 = A0 / B1
      B0 = B0 / B1
      A1 = A1 / B1
      B1 = 1

    return A1 / A
  

  def beta_cdf(Z, A, B):
    S = A + B
    BT = math.exp(log_gamma(S) - log_gamma(B) - log_gamma(A) + A * math.log(Z) +
      B * math.log(1 - Z))
    if (Z < (A + 1) / (S + 2)):
      Bcdf = BT * beta_inc(Z, A, B)
    else:
      Bcdf = 1 - BT * beta_inc(1 - Z, B, A)

    return Bcdf


  # bMean = bValue / bVisitors
  # mean = value / visitors
  # meanRatio = mean / bMean
  # 
  # Z = meanRatio / (meanRatio + visitors / bVisitors)
  # print "meanRatio", meanRatio
  # print "Z", Z
  # #  Degrees of freedom is 2 * n, beta_cdf takes 1/2 the degrees of freedon
  # print "bVisitors", bVisitors
  # print "visitors", visitors
  # 
  # pValue = beta_cdf(Z, bVisitors, visitors)
  # 
  # return pValue


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


def _variance(visitors, sum_of_values, sum_of_squares=None):
  if sum_of_squares is None:
    sum_of_squares = sum_of_values
  if visitors < 2:
    return None

  adjusted_mean_of_squares = _mean(visitors - 1, sum_of_squares)
  mean = _mean(visitors, sum_of_values)
  mean_squared = mean * mean
  mean_squared_coeff = float(visitors) / (visitors - 1)

  return adjusted_mean_of_squares - (mean_squared * mean_squared_coeff)


def log_gamma(Z):
  S = 1 + 76.18009173 / Z - 86.50532033 / (Z + 1) + 24.01409822 / (Z + 2) - \
  1.231739516 / (Z + 3) + .00120858003 / (Z + 4) - .00000536382 / (Z + 5)
  LG = (Z - .5) * math.log(Z + 4.5) - (Z + 4.5) + math.log(S * 2.50662827465)
  return LG


def beta_inc(X, A, B):
  A0 = 0
  B0 = 1
  A1 = 1
  B1 = 1
  M9 = 0
  A2 = 0
  C9 = 0
  while (abs((A1 - A2) / A1) > .00001):
    A2 = A1
    C9 = -(A + M9) * (A + B + M9) * X / (A + 2 * M9) / (A + 2 * M9 + 1)
    A0 = A1 + C9 * A0
    B0 = B1 + C9 * B0
    M9 = M9 + 1
    C9 = M9 * (B - M9) * X / (A + 2 * M9 - 1) / (A + 2 * M9)
    A1 = A0 + C9 * A1
    B1 = B0 + C9 * B1
    A0 = A0 / B1
    B0 = B0 / B1
    A1 = A1 / B1
    B1 = 1
  return A1 / A


def beta_cdf(Z, A, B):
  S = A + B
  BT = math.exp(log_gamma(S) - log_gamma(B) - log_gamma(A) + A * math.log(Z) +
    B * math.log(1 - Z))
  if (Z < (A + 1) / (S + 2)):
    Bcdf = BT * beta_inc(Z, A, B)
  else:
    Bcdf = 1 - BT * beta_inc(1 - Z, B, A)

  return Bcdf

# bVisitors, bValue, visitors, value = 3678, 46329.43, 3936,48519.80 
# bMean = bValue / bVisitors
# mean = value / visitors
# meanRatio = mean / bMean


# print "meanRatio", meanRatio
# print "Z:", Z
# #  Degrees of freedom is 2 * n, beta_cdf takes 1/2 the degrees of freedon
# print "bVisitors", bVisitors
# print "visitors", visitors

# pValue = beta_cdf(Z, bVisitors, visitors)

def expDist(bVisitors, bValue, visitors, value):

  meanRatio = (bValue/float(bVisitors))/(value/float(visitors))
  Z = meanRatio / (meanRatio  + float(visitors) / float(bVisitors))  
  if (meanRatio > 1):
     return beta_cdf(Z, bVisitors, visitors)
  else:
     return 1- beta_cdf(Z, bVisitors, visitors)
  
# print expDist(3678, 46329.43, 3936,48519.80)
#340994626
#from ExpDist import *
#bVisitors = 860
#visitors = 785
#bValue = 559498
#value = 506916
#meanRatio = (bValue/float(bVisitors))/(value/float(visitors))
#meanRatio
#expDist(bVisitors, bValue, visitors, value)
#
##409790592
#from ExpDist import *
#bVisitors = 17179
#visitors = 17190
#bValue = 8553498
#value = 8663566#
#meanRatio = (bValue/float(bVisitors))/(value/float(visitors))
#meanRatio
#expDist(bVisitors, bValue, visitors, value)
