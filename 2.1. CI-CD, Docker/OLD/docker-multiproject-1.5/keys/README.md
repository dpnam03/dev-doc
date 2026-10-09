Modify the ssh config
---------------------------------

	$ nano ~/.ssh/config

Then added

	Host docker-env
   		User git
   		HostName bitbucket.org
   		IdentityFile <path_to_docker_multiproject>/keys/id_rsa
   		IdentitiesOnly yes

Add submodule repo
---------------------------------------------

	$ git submodule add -b <branch> docker-env:bssdev03/docker-env.git docker

Init submodule
---------------------------------------------

	$ git submodule update --init

Pull new commit submodule
---------------------------------------------

	$ git submodule update --remote