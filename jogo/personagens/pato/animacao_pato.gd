## Decide qual animação o pato toca a partir do movimento.
## Lógica pura (sem nós), para poder ser testada sozinha.
class_name AnimacaoPato
extends RefCounted

## Velocidade (m/s) em que as animações de andar foram feitas para tocar no ritmo normal.
const VELOCIDADE_REFERENCIA := 1.2
## Abaixo disso o pato conta como parado.
const LIMIAR_PARADO := 0.15


## velocidade_local: velocidade no referencial do pato (-Z é a frente, +X é a direita dele).
static func escolher(velocidade_local: Vector3, no_chao: bool, agachado: bool) -> StringName:
	if not no_chao:
		return &"pular"
	if agachado:
		return &"agachar"
	var plano := Vector2(velocidade_local.x, velocidade_local.z)
	if plano.length() < LIMIAR_PARADO:
		return &"parado"
	if absf(plano.y) >= absf(plano.x):
		return &"andar_frente" if plano.y < 0.0 else &"andar_tras"
	return &"andar_direita" if plano.x > 0.0 else &"andar_esquerda"


## Velocidade de reprodução: correndo, as perninhas batem mais rápido.
static func ritmo(velocidade_plana: float) -> float:
	return clampf(velocidade_plana / VELOCIDADE_REFERENCIA, 0.5, 2.2)
