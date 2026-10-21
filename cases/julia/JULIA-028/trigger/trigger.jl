using Test
using JET

module Julia028Fixture
foo(value) = value < 0 ? value + string(value) : value
function bar(value)
    dynamic_result = foo(value)
    constant_result = foo(1)
    return dynamic_result, constant_result
end
end

println("JULIA-TRIGGER-START")
@testset "const-prop filtering preserves distinct callsite report" begin
    result = JET.report_call(Julia028Fixture.bar, (Int,))
    reports = JET.get_reports(result)
    @test length(reports) == 1
    report = only(reports)
    @test report isa JET.MethodErrorReport
    @test report.t === Tuple{typeof(+),Int,String}
end
