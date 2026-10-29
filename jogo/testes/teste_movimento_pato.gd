extends Teste
## Entrada no formato do Input.get_vector: x = direita, y = trás (frente é y negativo).


func test_frente_sem_girar_a_camera() -> void:
	perto(MovimentoPato.direcao(Vector2(0, -1), 0.0), Vector3(0, 0, -1))


func test_camera_girada_90_graus_para_a_esquerda() -> void:
	perto(MovimentoPato.direcao(Vector2(0, -1), PI / 2), Vector3(-1, 0, 0))


func test_diagonal_nao_fica_mais_rapida() -> void:
	perto(MovimentoPato.direcao(Vector2(1, -1), 0.0).length(), 1.0)


func test_sem_entrada_fica_parado() -> void:
	perto(MovimentoPato.direcao(Vector2.ZERO, 1.0), Vector3.ZERO)


func test_velocidades() -> void:
	perto(MovimentoPato.velocidade_alvo(false, false), MovimentoPato.ANDAR, "andar:")
	perto(MovimentoPato.velocidade_alvo(true, false), MovimentoPato.CORRER, "correr:")
	perto(MovimentoPato.velocidade_alvo(true, true), MovimentoPato.AGACHADO, "agachado ignora o correr:")


func test_quack_curto_ou_forte() -> void:
	igual(MovimentoPato.quack_forte(0.1), false, "clique rápido:")
	igual(MovimentoPato.quack_forte(0.4), true, "segurou:")
