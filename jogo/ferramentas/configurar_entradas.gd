## Cria os controles do jogo no project.godot (seção [input]).
## Rodar de novo restaura os controles padrão:
##   godot --headless --path jogo --script res://ferramentas/configurar_entradas.gd
extends SceneTree


func _init() -> void:
	var teclas := {
		"mover_frente": KEY_W,
		"mover_tras": KEY_S,
		"mover_esquerda": KEY_A,
		"mover_direita": KEY_D,
		"correr": KEY_SHIFT,
		"agachar": KEY_CTRL,
		"pular": KEY_SPACE,
		"soltar_mouse": KEY_ESCAPE,
	}
	for acao: String in teclas:
		var evento := InputEventKey.new()
		evento.physical_keycode = teclas[acao]
		_salvar_acao(acao, [evento])

	var clique := InputEventMouseButton.new()
	clique.button_index = MOUSE_BUTTON_LEFT
	_salvar_acao("grasnar", [clique])

	var erro := ProjectSettings.save()
	print("Controles salvos." if erro == OK else "Erro ao salvar: %s" % error_string(erro))
	quit(erro)


func _salvar_acao(acao: String, eventos: Array) -> void:
	for evento: InputEvent in eventos:
		evento.device = -1  # qualquer teclado/mouse
	ProjectSettings.set_setting("input/" + acao, {"deadzone": 0.2, "events": eventos})
