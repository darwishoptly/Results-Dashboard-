
import logging
import math
def log_gamma(Z):
	S = 1 + 76.18009173 / Z - 86.50532033 / (Z + 1) + 24.01409822 / (Z + 2) - 1.231739516 / (Z + 3) + .00120858003 / (Z + 4) - .00000536382 / (Z + 5)
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
# def revenue_p_value(bVisitors, bValue, visitors, value):
bVisitors, bValue, visitors, value = 2*3768, 12.59464, 2*3936, 12.3272
bMean = float(bValue) / float(bVisitors)
mean = float(value) / float(visitors)
meanRatio = float(mean) / bMean
Z = meanRatio / (meanRatio + visitors / bVisitors)
#  Degrees of freedom is 2 * n, beta_cdf takes 1/2 the degrees of freedon
pValue = beta_cdf(Z, bVisitors, visitors)
print pValue

