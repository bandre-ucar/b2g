Utility to manage github organization members.

# Installation instructions:
1. clone repo
1. install virtualenv and create environment
```sh
    $ pip install virtualenv
    $ cd cseg-mug
    $ make env
    # install dependencies
    $ make develop  
    # activate the virtualenv in bash
    $ . ./env/bin/activate  
    
```
3. create a mug.cfg file
```sh
    $ touch ../mug.cfg
    $ cat > ../mug.cfg <EOF
    [github]
    user=
    token=
    organization=
    EOF
```   
4. Note: you will need to create a github token for the API to work correctly under your user settings. 
   We don't recommend giving token access to private keys or deleting repos. 
   You can test the token against a repo using:
```sh
     $ curl  -H "Authorization: bearer ${github_auth_token}" -i "https://api.github.com/repos/cseg-test/test-repo1/invitations"
```
5. run the script:
```sh     
     mug.py --help
```
