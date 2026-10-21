using JuliaSyntax
println("JULIA-TRIGGER-START")
src = repeat('a', 1000) * '\n' * "@hi"
actual = Expr(parsestmt(SyntaxNode, SubString(src, 1001:lastindex(src))))
expected = Expr(:macrocall, Symbol("@hi"), LineNumberNode(2))
actual == expected || error("SubString syntax conversion incorrect: $(actual)")
println("JULIA-640 trigger completed")
