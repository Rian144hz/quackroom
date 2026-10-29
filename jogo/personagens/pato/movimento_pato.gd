## Regras de movimento do pato. Lógica pura (sem nós), testada em testes/teste_movimento_pato.gd.
class_name MovimentoPato
extends RefCounted

const ANDAR := 1.2  ## m/s
const CORRER := 2.4
const AGACHADO := 0.6
## Segurar o clique por mais que isso vira quack forte.
const SEGUNDOS_QUACK_FORTE := 0.25


## entrada: como Input.get_vector (x = direita, y = trás). yaw: giro da câmera em radianos.
## Devolve a direção no mundo, com tamanho no máximo 1 (diagonal não fica mais rápida).
static func direcao(entrada: Vector2, yaw: float) -> Vector3:
	var local := Vector3(entrada.x, 0.0, entrada.y).limit_length(1.0)
	return local.rotated(Vector3.UP, yaw)


static func velocidade_alvo(correndo: bool, agachado: bool) -> float:
	if agachado:
		return AGACHADO
	return CORRER if correndo else ANDAR


static func quack_forte(segundos_segurando: float) -> bool:
	return segundos_segurando >= SEGUNDOS_QUACK_FORTE
