## Contas das animações do pato: onde ele está no blend space, ritmo das patinhas e amassado.
## Lógica pura (sem nós), testada em testes/teste_animacao_pato.gd.
class_name AnimacaoPato
extends RefCounted

## Velocidade (m/s) em que as animações de andar foram feitas para tocar no ritmo normal.
const VELOCIDADE_REFERENCIA := 1.2


## Converte a velocidade (referencial do pato: -Z frente, +X direita) para o BlendSpace2D:
## centro = parado, +Y = andar_frente, -Y = andar_tras, +X = andar_direita, -X = andar_esquerda.
## Velocidades acima de andar ficam na borda; quem acelera as perninhas é o ritmo().
static func posicao_blend(velocidade_local: Vector3) -> Vector2:
	var plano := Vector2(velocidade_local.x, -velocidade_local.z) / VELOCIDADE_REFERENCIA
	return plano.limit_length(1.0)


## Velocidade de reprodução: correndo, as perninhas batem mais rápido.
static func ritmo(velocidade_plana: float) -> float:
	return clampf(velocidade_plana / VELOCIDADE_REFERENCIA, 1.0, 2.2)


## Escala do "amassado": positivo achata (pouso), negativo estica (pulo).
## Alarga dos lados metade do que achata, para parecer que o volume se mantém.
static func amassado(intensidade: float) -> Vector3:
	return Vector3(1.0 + intensidade / 2.0, 1.0 - intensidade, 1.0 + intensidade / 2.0)
