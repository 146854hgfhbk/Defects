println("JULIA-TRIGGER-START")
using Test
using HypothesisTests

@testset "JULIA-284 Mann-Whitney pvalue clamped" begin
    a = [1.34937, 1.75722, 0.276514, 1.04546, 1.69085, 0.738085, 2.36313]
    b = [2.62325, 1.16533, 1.1327, 0.728714]
    @test pvalue(ExactMannWhitneyUTest(a, b); tail=:both) == 1
    a = [12, 10, 7, 6, 3, 1]
    b = [11, 9, 8, 5, 4, 2]
    @test pvalue(MannWhitneyUTest(a, b); tail=:both) == 1
end
