using Test
using Unitful

println("JULIA-TRIGGER-START")

@testset "large unit powers cancel before conversion" begin
    @test uconvert(u"kb^1000", 1u"kb^1001 * b^-1") === 1000u"kb^1000"
    @test uconvert(u"kOe^1000", 1u"kOe^1001 * Oe^-1") === 1000u"kOe^1000"
end

println("JULIA-738 trigger completed")
