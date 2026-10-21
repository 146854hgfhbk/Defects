using IntervalArithmetic

# Exact reproducer from issue #601. `one` for an existing Complex interval
# type must have a zero imaginary component; no newly added API is used.
x = one(Complex{Interval{Float64}})

@assert isthin(real(x), 1.0)
@assert isthinzero(imag(x))
