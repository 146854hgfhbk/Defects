using Test
using JET

# Reuse the upstream test utility solely to invoke JET's top-level analysis
# entry point and classify its public report object; the oracle below is the
# end-to-end regression assertion from the fix commit.
include(joinpath(pkgdir(JET), "test", "interactive_utils.jl"))

println("JULIA-TRIGGER-START")

context = Module()
Core.eval(context, :(using Test))

@testset "JULIA-557 conditional closure analysis" begin
    result = @analyze_toplevel context = context virtualize = false begin
        items = [1]
        @test_broken any(items) do _
            missing_name_in_conditional_closure
        end && any(items) do _
            false
        end
    end
    @test isempty(result.res.toplevel_error_reports)
    @test any(result.res.inference_error_reports) do report
        is_global_undef_var(report, :missing_name_in_conditional_closure)
    end
end
