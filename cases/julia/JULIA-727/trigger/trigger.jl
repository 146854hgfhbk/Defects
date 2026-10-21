using Test
using BasicBSpline

println("JULIA-TRIGGER-START")
@testset "degenerate derivative spaces" begin
    p1 = BSplineSpace{2}(KnotVector(1:8))
    p2 = BSplineSpace{2}(knotvector"111111151111")
    dp1 = BSplineDerivativeSpace{1}(p1)
    dp2 = BSplineDerivativeSpace{1}(p2)
    @test isdegenerate_R(p1) == isdegenerate_R(dp1)
    @test isdegenerate_R(p2) == isdegenerate_R(dp2)
    @test isdegenerate_I(p1) == isdegenerate_I(dp1)
    @test isdegenerate_I(p2) == isdegenerate_I(dp2)
    for i in 1:dim(p1)
        @test isdegenerate_R(p1, i) == isdegenerate_R(dp1, i)
        @test isdegenerate_I(p1, i) == isdegenerate_I(dp1, i)
    end
    for i in 1:dim(p2)
        @test isdegenerate_R(p2, i) == isdegenerate_R(dp2, i)
        @test isdegenerate_I(p2, i) == isdegenerate_I(dp2, i)
    end
end
