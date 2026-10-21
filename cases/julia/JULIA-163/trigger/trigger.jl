println("JULIA-TRIGGER-START")
using Test
using JuliaSyntax

@testset "JULIA-163 incomplete multiline comments" begin
    JuliaSyntax.enable_in_core!()
    try
        for (source, tag) in (("function f()\nbody #comment", :block),
                              ("a = [\n1,\n2, #comment", :other))
            statement = JuliaSyntax.core_parser_hook(source, "trigger", 1, 0, :statement)[1]
            @test Base.incomplete_tag(statement) == tag
            all_expr = JuliaSyntax.core_parser_hook(source, "trigger", 1, 0, :all)[1]
            @test all_expr isa Expr && all_expr.head == :toplevel
            @test Base.incomplete_tag(all_expr.args[end]) == tag
        end
    finally
        JuliaSyntax.enable_in_core!(false)
    end
end
