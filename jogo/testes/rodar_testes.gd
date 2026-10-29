## Roda todos os arquivos testes/teste_*.gd sem abrir janela:
##   godot --headless --path jogo --script res://testes/rodar_testes.gd
## Sai com código 1 se algum teste falhar.
extends SceneTree


func _init() -> void:
	var total := 0
	var falharam := 0
	for arquivo in DirAccess.get_files_at("res://testes"):
		if not (arquivo.begins_with("teste_") and arquivo.ends_with(".gd")):
			continue
		var script: GDScript = load("res://testes/" + arquivo)
		if script == null or not script.can_instantiate():
			total += 1
			falharam += 1
			print("  FALHOU  %s :: não compila (veja o erro acima)" % arquivo)
			continue
		var caso: Teste = script.new()
		for metodo in caso.get_method_list():
			var nome: String = metodo.name
			if not nome.begins_with("test_"):
				continue
			caso.falhas.clear()
			caso.call(nome)
			total += 1
			if caso.falhas.is_empty():
				print("  ok      %s :: %s" % [arquivo, nome])
			else:
				falharam += 1
				print("  FALHOU  %s :: %s" % [arquivo, nome])
				for falha in caso.falhas:
					print("          " + falha)
	print("\n%d testes, %d falharam" % [total, falharam])
	quit(1 if falharam else 0)
