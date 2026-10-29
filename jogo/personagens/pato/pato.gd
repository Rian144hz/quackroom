## O pato do jogador em 3ª pessoa.
## - O mouse gira só a câmera, livre em volta do pato.
## - Andando, o pato vira suavemente para onde a câmera olha; parado, fica onde está.
## - As animações são MISTURADAS num AnimationTree (veja _montar_animacoes), e um "tempero"
##   feito por código deixa tudo menos duro: inclina ao acelerar, tomba nas curvas, estica no
##   pulo e amassa no pouso.
## As contas ficam em MovimentoPato e AnimacaoPato (testadas); aqui é a ligação com o Godot.
class_name Pato
extends CharacterBody3D

## Emitido quando o pato grasna. O SomBus (etapa 3) vai transformar isso em onda de sonar.
signal grasnou(forte: bool)

const ACELERACAO := 10.0  ## m/s²: quão rápido o pato chega na velocidade desejada
const VELOCIDADE_PULO := 2.6
const QUEDA_PLANANDO := 0.8  ## segurando Espaço no ar, cai no máximo nessa velocidade
const SENSIBILIDADE_MOUSE := 0.003
const ALTURA_CAMERA := 0.45
const RAPIDEZ_GIRO := 10.0  ## quão rápido o pato vira para onde a câmera olha
const RAPIDEZ_CAMERA := 14.0  ## quão grudada a câmera segue o pato
const RAPIDEZ_MISTURA := 9.0  ## quão rápido uma animação se mistura na outra
## Se a parede empurra a câmera para mais perto que isso, o pato some (senão a câmera entra nele).
const DISTANCIA_MINIMA_CAMERA := 0.35
const ANIMACOES_EM_LOOP: Array[StringName] = [
	&"parado", &"andar_frente", &"andar_tras", &"andar_esquerda", &"andar_direita", &"agachar",
]
## O grasnar mexe só nesses ossos: as pernas continuam andando enquanto ele grasna.
const OSSOS_DO_GRASNAR: Array[String] = [
	"Esqueleto/Skeleton3D:corpo", "Esqueleto/Skeleton3D:cabeca",
	"Esqueleto/Skeleton3D:asa.L", "Esqueleto/Skeleton3D:asa.R",
]

var _gravidade: float = ProjectSettings.get_setting("physics/3d/default_gravity")
var _segurando_quack := false
var _tempo_segurando := 0.0
var _arvore: AnimationTree
# valores que se aproximam do alvo aos poucos (é isso que deixa a animação macia)
var _blend := Vector2.ZERO
var _peso_agachado := 0.0
var _peso_no_ar := 0.0
var _amassado := 0.0
var _inclinacao := Vector2.ZERO  ## x = para frente, y = para o lado
var _estava_no_chao := true
var _giro_anterior := 0.0
## O jogador quer o mouse preso? (Esc solta; clicar na janela prende de novo.)
var _quer_mouse_preso := true

@onready var _visual: Node3D = $Visual
@onready var _pivo_camera: Node3D = $PivoCamera
@onready var _braco_camera: SpringArm3D = $PivoCamera/Braco
@onready var _animacoes: AnimationPlayer = $Visual/Modelo/AnimationPlayer


func _ready() -> void:
	# O PivoCamera é "top_level": não herda a rotação do pato, só segue a posição dele.
	_pivo_camera.global_position = global_position + Vector3.UP * ALTURA_CAMERA
	_pivo_camera.rotation.y = rotation.y
	_braco_camera.add_excluded_object(get_rid())  # a câmera não "bate" no próprio pato
	_giro_anterior = rotation.y
	_montar_animacoes()
	_prender_mouse(true)


## No Linux, prender o mouse falha se a janela ainda não está em foco ("NO GRAB"),
## então tentamos de novo sempre que a janela ganha foco.
func _notification(aviso: int) -> void:
	if aviso == NOTIFICATION_APPLICATION_FOCUS_IN and _quer_mouse_preso:
		_prender_mouse(true)


func _prender_mouse(preso: bool) -> void:
	_quer_mouse_preso = preso
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED if preso else Input.MOUSE_MODE_VISIBLE


func _unhandled_input(evento: InputEvent) -> void:
	if Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
		if evento is InputEventMouseButton and evento.pressed:
			_prender_mouse(true)  # clicar na janela volta pro jogo (esse clique não grasna)
		return

	if evento is InputEventMouseMotion:
		_pivo_camera.rotation.y -= evento.relative.x * SENSIBILIDADE_MOUSE
		_pivo_camera.rotation.x = clampf(
			_pivo_camera.rotation.x - evento.relative.y * SENSIBILIDADE_MOUSE,
			deg_to_rad(-55.0), deg_to_rad(25.0))
	elif evento.is_action_pressed(&"soltar_mouse"):
		_prender_mouse(false)
	elif evento.is_action_pressed(&"grasnar"):
		_segurando_quack = true
		_tempo_segurando = 0.0
	elif evento.is_action_released(&"grasnar") and _segurando_quack:
		_segurando_quack = false
		_grasnar(MovimentoPato.quack_forte(_tempo_segurando))


func _physics_process(delta: float) -> void:
	if _segurando_quack:
		_tempo_segurando += delta
	var agachado := Input.is_action_pressed(&"agachar")
	var correndo := Input.is_action_pressed(&"correr")

	if not is_on_floor():
		velocity.y -= _gravidade * delta
		if Input.is_action_pressed(&"pular"):
			velocity.y = maxf(velocity.y, -QUEDA_PLANANDO)  # bate as asas e plana
	elif Input.is_action_just_pressed(&"pular") and not agachado:
		velocity.y = VELOCIDADE_PULO

	var entrada := Input.get_vector(&"mover_esquerda", &"mover_direita", &"mover_frente", &"mover_tras")
	var giro_camera := _pivo_camera.rotation.y
	var alvo := MovimentoPato.direcao(entrada, giro_camera) * MovimentoPato.velocidade_alvo(correndo, agachado)
	velocity.x = move_toward(velocity.x, alvo.x, ACELERACAO * delta)
	velocity.z = move_toward(velocity.z, alvo.z, ACELERACAO * delta)
	if entrada != Vector2.ZERO:
		rotation.y = lerp_angle(rotation.y, giro_camera, MovimentoPato.suavizar(RAPIDEZ_GIRO, delta))

	var velocidade_antes := velocity  # move_and_slide zera a queda ao tocar o chão
	move_and_slide()

	_seguir_com_a_camera(delta)
	_atualizar_animacoes(delta, agachado, entrada != Vector2.ZERO)
	_temperar(delta, velocidade_antes)


func _seguir_com_a_camera(delta: float) -> void:
	var alvo := global_position + Vector3.UP * ALTURA_CAMERA
	_pivo_camera.global_position = _pivo_camera.global_position.lerp(
		alvo, MovimentoPato.suavizar(RAPIDEZ_CAMERA, delta))
	_visual.visible = _braco_camera.get_hit_length() > DISTANCIA_MINIMA_CAMERA


## Monta o AnimationTree em código (é o mesmo que montar no editor, nó por nó):
##   locomoção (BlendSpace2D) → ritmo (TimeScale) → agachar (Blend2) → no_ar (Blend2) → grasnar (OneShot)
func _montar_animacoes() -> void:
	for nome in ANIMACOES_EM_LOOP:
		_animacoes.get_animation(nome).loop_mode = Animation.LOOP_LINEAR

	var arvore := AnimationNodeBlendTree.new()

	var locomocao := AnimationNodeBlendSpace2D.new()
	var pontos := {
		&"parado": Vector2(0, 0), &"andar_frente": Vector2(0, 1), &"andar_tras": Vector2(0, -1),
		&"andar_direita": Vector2(1, 0), &"andar_esquerda": Vector2(-1, 0),
	}
	for nome: StringName in pontos:
		locomocao.add_blend_point(_no_animacao(nome), pontos[nome], -1, nome)
	arvore.add_node(&"locomocao", locomocao)
	arvore.add_node(&"ritmo", AnimationNodeTimeScale.new())

	arvore.add_node(&"agachado", _no_animacao(&"agachar"))
	arvore.add_node(&"agachar", AnimationNodeBlend2.new())

	# No ar: só o trecho do "pular" em que ele bate as asas (quadros 8 a 20), em loop.
	var voando := _no_animacao(&"pular")
	voando.use_custom_timeline = true
	voando.start_offset = 8.0 / 24.0
	voando.timeline_length = 12.0 / 24.0
	voando.stretch_time_scale = false
	voando.loop_mode = Animation.LOOP_LINEAR
	arvore.add_node(&"voando", voando)
	arvore.add_node(&"no_ar", AnimationNodeBlend2.new())

	var grasnar := AnimationNodeOneShot.new()
	grasnar.fadein_time = 0.05
	grasnar.fadeout_time = 0.15
	grasnar.filter_enabled = true
	for osso in OSSOS_DO_GRASNAR:
		grasnar.set_filter_path(NodePath(osso), true)
	arvore.add_node(&"grasnando", _no_animacao(&"grasnar"))
	arvore.add_node(&"grasnar", grasnar)

	arvore.connect_node(&"ritmo", 0, &"locomocao")
	arvore.connect_node(&"agachar", 0, &"ritmo")
	arvore.connect_node(&"agachar", 1, &"agachado")
	arvore.connect_node(&"no_ar", 0, &"agachar")
	arvore.connect_node(&"no_ar", 1, &"voando")
	arvore.connect_node(&"grasnar", 0, &"no_ar")
	arvore.connect_node(&"grasnar", 1, &"grasnando")
	arvore.connect_node(&"output", 0, &"grasnar")

	_arvore = AnimationTree.new()
	_arvore.name = "Animacoes"
	_arvore.tree_root = arvore
	_animacoes.get_parent().add_child(_arvore)
	_arvore.anim_player = _arvore.get_path_to(_animacoes)
	_arvore.active = true


func _no_animacao(nome: StringName) -> AnimationNodeAnimation:
	var no := AnimationNodeAnimation.new()
	no.animation = nome
	return no


func _atualizar_animacoes(delta: float, agachado: bool, andando: bool) -> void:
	var peso := MovimentoPato.suavizar(RAPIDEZ_MISTURA, delta)
	var velocidade_local := global_transform.basis.inverse() * velocity
	_blend = _blend.lerp(AnimacaoPato.posicao_blend(velocidade_local), peso)
	# agachado andando: deixa um pouco das perninhas aparecer por baixo
	var alvo_agachado := (0.7 if andando else 1.0) if agachado else 0.0
	_peso_agachado = lerpf(_peso_agachado, alvo_agachado, peso)
	_peso_no_ar = lerpf(_peso_no_ar, 0.0 if is_on_floor() else 1.0, peso)

	_arvore.set(&"parameters/locomocao/blend_position", _blend)
	_arvore.set(&"parameters/ritmo/scale", AnimacaoPato.ritmo(Vector2(velocity.x, velocity.z).length()))
	_arvore.set(&"parameters/agachar/blend_amount", _peso_agachado)
	_arvore.set(&"parameters/no_ar/blend_amount", _peso_no_ar)


## O "tempero": pequenos movimentos do corpo inteiro que a animação sozinha não dá.
func _temperar(delta: float, velocidade_antes: Vector3) -> void:
	var no_chao := is_on_floor()
	if no_chao and not _estava_no_chao:
		_amassado = clampf(-velocidade_antes.y * 0.09, 0.06, 0.3)  # quanto maior a queda, mais amassa
	elif not no_chao and _estava_no_chao and velocity.y > 0.0:
		_amassado = -0.15  # estica ao sair do chão
	_estava_no_chao = no_chao
	_amassado = lerpf(_amassado, 0.0, MovimentoPato.suavizar(10.0, delta))

	var velocidade_local := global_transform.basis.inverse() * velocity
	var velocidade_giro := wrapf(rotation.y - _giro_anterior, -PI, PI) / delta
	_giro_anterior = rotation.y
	var alvo := Vector2(
		clampf(-velocidade_local.z * 0.08, -0.15, 0.2),  # inclina para onde anda
		clampf(velocidade_giro * 0.05 - velocidade_local.x * 0.05, -0.2, 0.2))  # tomba na curva
	_inclinacao = _inclinacao.lerp(alvo, MovimentoPato.suavizar(8.0, delta))
	_visual.transform.basis = (Basis.from_euler(Vector3(-_inclinacao.x, 0.0, _inclinacao.y))
		* Basis.from_scale(AnimacaoPato.amassado(_amassado)))


func _grasnar(forte: bool) -> void:
	_arvore.set(&"parameters/grasnar/request", AnimationNodeOneShot.ONE_SHOT_REQUEST_FIRE)
	grasnou.emit(forte)
