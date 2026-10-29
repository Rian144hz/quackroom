extends Teste
## A animação vem da velocidade no referencial do pato: -Z é frente, +X é a direita dele.


func test_parado_quando_quase_sem_velocidade() -> void:
	igual(AnimacaoPato.escolher(Vector3(0.05, 0, -0.05), true, false), &"parado")


func test_quatro_direcoes() -> void:
	igual(AnimacaoPato.escolher(Vector3(0, 0, -1.2), true, false), &"andar_frente", "frente:")
	igual(AnimacaoPato.escolher(Vector3(0, 0, 1.2), true, false), &"andar_tras", "trás:")
	igual(AnimacaoPato.escolher(Vector3(1.2, 0, 0), true, false), &"andar_direita", "direita:")
	igual(AnimacaoPato.escolher(Vector3(-1.2, 0, 0), true, false), &"andar_esquerda", "esquerda:")


func test_diagonal_usa_a_direcao_dominante() -> void:
	igual(AnimacaoPato.escolher(Vector3(0.5, 0, -1.0), true, false), &"andar_frente")
	igual(AnimacaoPato.escolher(Vector3(-1.0, 0, 0.5), true, false), &"andar_esquerda")


func test_no_ar_sempre_pular() -> void:
	igual(AnimacaoPato.escolher(Vector3(0, -2, -1), false, false), &"pular")
	igual(AnimacaoPato.escolher(Vector3.ZERO, false, true), &"pular", "mesmo agachado:")


func test_agachado_no_chao() -> void:
	igual(AnimacaoPato.escolher(Vector3(0, 0, -0.6), true, true), &"agachar")


func test_ritmo_acompanha_a_velocidade() -> void:
	perto(AnimacaoPato.ritmo(AnimacaoPato.VELOCIDADE_REFERENCIA), 1.0, "andando:")
	verdadeiro(AnimacaoPato.ritmo(2.4) > 1.5, "correndo acelera a animação")
	perto(AnimacaoPato.ritmo(0.0), 0.5, "nunca fica lento demais:")
