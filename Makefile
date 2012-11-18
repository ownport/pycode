test-unittest:
	@ echo '***************************'
	@ echo '*       Unittests         *'
	@ echo '***************************'
	python tests/test_utils.py
	python tests/test_pycodestruct.py

graph:
	@ dot -T png docs/pycode.gv -o docs/pycode.png && eog docs/pycode.png

