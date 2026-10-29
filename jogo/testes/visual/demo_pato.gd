## Demo automática: "joga sozinha" para conferir animações e câmera sem precisar jogar.
## Grava em quadros PNG com o Movie Maker do Godot:
##   godot --path jogo --write-movie /tmp/demo/pato.png --fixed-fps 30 --quit-after 345 res://testes/visual/demo_pato.tscn
extends Node

## [ação, começa (s), termina (s)]
const ROTEIRO := [
	[&"mover_frente", 0.6, 2.2],
	[&"mover_direita", 2.2, 3.4],
	[&"mover_tras", 3.4, 4.4],
	[&"mover_frente", 4.4, 6.0],
	[&"correr", 4.4, 6.0],
	[&"pular", 6.2, 7.4],
	[&"agachar", 9.6, 11.0],
	[&"mover_frente", 9.6, 11.0],
]
## [segundo, segurar o quack por quantos segundos]
const QUACKS := [[7.8, 0.05], [8.6, 0.4]]

var _tempo := 0.0


func _physics_process(delta: float) -> void:
	_tempo += delta
	var ligadas := {}
	for passo in ROTEIRO:
		if _tempo >= passo[1] and _tempo < passo[2]:
			ligadas[passo[0]] = true
	for passo in ROTEIRO:
		var acao: StringName = passo[0]
		if ligadas.has(acao) and not Input.is_action_pressed(acao):
			Input.action_press(acao)
		elif not ligadas.has(acao) and Input.is_action_pressed(acao):
			Input.action_release(acao)
	if _tempo > 4.4 and _tempo < 6.0:
		_mouse(Vector2(5, 0))  # gira a câmera enquanto corre
	for quack in QUACKS:
		if _passou(quack[0], delta):
			_quack(true)
		if _passou(quack[0] + quack[1], delta):
			_quack(false)


func _passou(instante: float, delta: float) -> bool:
	return _tempo >= instante and _tempo - delta < instante


func _quack(apertado: bool) -> void:
	var evento := InputEventAction.new()
	evento.action = &"grasnar"
	evento.pressed = apertado
	Input.parse_input_event(evento)


func _mouse(movimento: Vector2) -> void:
	var evento := InputEventMouseMotion.new()
	evento.relative = movimento
	Input.parse_input_event(evento)
