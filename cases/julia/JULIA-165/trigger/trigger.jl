using Test
using JET

include(joinpath(pkgdir(JET), "test", "interactive_utils.jl"))

println("JULIA-TRIGGER-START")
@testset "top-level closure in abstract loop" begin
    result = @analyze_toplevel begin
        function calc_kite_pos(turn_angle)
            return [cos(turn_angle), sin(turn_angle), 0.0]
        end

        const THETA = [30, 45, 60, 75]
        turn_angles = 0:1:360
        ys_all = Vector{Vector{Float64}}()
        for theta in THETA
            push!(ys_all, [calc_kite_pos(deg2rad(angle))[2] for angle in turn_angles])
        end
    end
    @test isempty(result.res.toplevel_error_reports)
    @test isempty(result.res.inference_error_reports)
end
