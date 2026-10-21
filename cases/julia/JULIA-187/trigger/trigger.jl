using Test
using Optim

println("JULIA-TRIGGER-START")
@testset "subspace backtracking measures from the Cauchy point" begin
    objective(x) = (1.0 - x[1])^2 + 100.0 * (x[2] - x[1]^2)^2
    function gradient!(gradient, x)
        gradient[1] = -2.0 * (1.0 - x[1]) - 400.0 * (x[2] - x[1]^2) * x[1]
        gradient[2] = 200.0 * (x[2] - x[1]^2)
        return gradient
    end
    lower = [-0.6246061824346689, -1.3848789693740542]
    upper = [1.2952187059881008, 0.42144488961717363]
    initial = [-0.6246061824346689, 0.42144488961717363]
    result = optimize(objective, gradient!, lower, upper, initial, LBFGSB(m=5))
    @test Optim.converged(result)
    @test Optim.minimum(result) ≈ 0.12234569775490675 atol=1e-8
    @test Optim.f_calls(result) <= 55
end
