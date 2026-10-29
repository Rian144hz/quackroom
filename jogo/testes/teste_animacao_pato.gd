extends Teste
## A velocidade vem no referencial do pato: -Z é a frente, +X é a direita dele.


func test_posicao_no_blend_space() -> void:
	var andar := AnimacaoPato.VELOCIDADE_REFERENCIA
	perto(AnimacaoPato.posicao_blend(Vector3.ZERO), Vector2.ZERO, "parado no centro:")
	perto(AnimacaoPato.posicao_blend(Vector3(0, 0, -andar)), Vector2(0, 1), "frente é +Y:")
	perto(AnimacaoPato.posicao_blend(Vector3(andar, 0, 0)), Vector2(1, 0), "direita é +X:")
	perto(AnimacaoPato.posicao_blend(Vector3(0, 0, andar / 2)), Vector2(0, -0.5), "meio passo para trás:")


func test_blend_ignora_a_queda_e_nao_passa_da_borda() -> void:
	perto(AnimacaoPato.posicao_blend(Vector3(0, -5, 0)), Vector2.ZERO, "cair não é andar:")
	perto(AnimacaoPato.posicao_blend(Vector3(0, 0, -10)).length(), 1.0, "correndo fica na borda:")


func test_amassado_de_pouso() -> void:
	perto(AnimacaoPato.amassado(0.0), Vector3.ONE, "sem amassar:")
	var pouso := AnimacaoPato.amassado(0.2)
	perto(pouso.y, 0.8, "baixa ao aterrissar:")
	verdadeiro(pouso.x > 1.0 and pouso.z > 1.0, "e alarga dos lados")
	verdadeiro(AnimacaoPato.amassado(-0.1).y > 1.0, "valor negativo estica (pulo)")


func test_ritmo_acompanha_a_velocidade() -> void:
	perto(AnimacaoPato.ritmo(AnimacaoPato.VELOCIDADE_REFERENCIA), 1.0, "andando:")
	verdadeiro(AnimacaoPato.ritmo(2.4) > 1.5, "correndo acelera a animação")
	perto(AnimacaoPato.ritmo(0.0), 1.0, "parado respira no ritmo normal:")
