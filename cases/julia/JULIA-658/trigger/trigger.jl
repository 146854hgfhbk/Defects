# JULIA-658 trigger: NaN-safe mode differential (upstream ForwardDiff PR #777).
# Assertions verbatim from the upstream test files at the fixed revision.
# Both revisions default nansafe_mode=false; the preference override below
# selects the NaN-safe mode the upstream testsets are written to exercise.
ENV["JULIA_FORWARDDIFF_nansafe_mode"] = "true"
import Preferences
Preferences.set_preferences!("ForwardDiff", "nansafe_mode" => true)
# (writes LocalPreferences.toml in the active project so precompile bakes nansafe=true)
using Test, ForwardDiff, NaNMath
println("JULIA-TRIGGER-START")

@testset "NaN-safe mode" begin
    x = ForwardDiff.derivative(log ∘ zero, 1.0)
    if ForwardDiff.NANSAFE_MODE_ENABLED
        @test iszero(x)
    else
        @test isnan(x)
    end
end

@testset "exponential function at base zero" begin
    if ForwardDiff.NANSAFE_MODE_ENABLED
        @test isequal(ForwardDiff.gradient(t -> t[1]^t[2], [0.0, -0.5]), [-Inf, -Inf])
        @test isequal(ForwardDiff.gradient(t -> t[1]^t[2], [0.0,  0.0]), [NaN, -Inf])
        @test isequal(ForwardDiff.gradient(t -> t[1]^t[2], [0.0,  0.5]), [Inf, 0.0])
    else
        @test isequal(ForwardDiff.gradient(t -> t[1]^t[2], [0.0, -0.5]), [NaN, NaN])
        @test isequal(ForwardDiff.gradient(t -> t[1]^t[2], [0.0,  0.0]), [NaN, NaN])
        @test isequal(ForwardDiff.gradient(t -> t[1]^t[2], [0.0,  0.5]), [Inf, NaN])
    end
    @test isequal(ForwardDiff.gradient(t -> t[1]^t[2], [0.0,  1.5]), [0.0, 0.0])
end

@testset "gradient for exponential with NaNMath" begin
    if ForwardDiff.NANSAFE_MODE_ENABLED
        @test isequal(ForwardDiff.gradient(x -> NaNMath.pow(x[1],x[2]), [NaN, 1.0]), [1.0, NaN])
    else
        @test isequal(ForwardDiff.gradient(x -> NaNMath.pow(x[1],x[2]), [NaN, 1.0]), [NaN, NaN])
    end
    @test ForwardDiff.gradient(x -> NaNMath.pow(x[1], x[2]), [1.0, 1.0]) == [1.0, 0.0]
    @test isnan(ForwardDiff.gradient((x) -> NaNMath.pow(x[1], x[2]), [-1.0, 0.5])[1])

    if ForwardDiff.NANSAFE_MODE_ENABLED
        @test isequal(ForwardDiff.gradient(x -> x[1]^x[2], [NaN, 1.0]), [1.0, NaN])
    else
        @test isequal(ForwardDiff.gradient(x -> x[1]^x[2], [NaN, 1.0]), [NaN, NaN])
    end
    @test ForwardDiff.gradient(x -> x[1]^x[2], [1.0, 1.0]) == [1.0, 0.0]
    @test_throws DomainError ForwardDiff.gradient(x -> x[1]^x[2], [-1.0, 0.5])
end
println("JULIA-658 trigger completed")
