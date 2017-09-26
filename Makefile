env : FORCE
	virtualenv --python=python $@

develop : FORCE
	. env/bin/activate; python setup.py $@

clean : FORCE
	rm -rf *~

clobber : clean
	rm -rf env

FORCE :
