#!/bin/sh

clear
echo "***************************************************************"
echo "*                                                             *"
echo "*            INSTALLING allsky.py by Oleg Milantiev           *"
echo "*       https://github.com/oleg-milantiev/allsky.py/wiki      *"
echo "*                                                             *"
echo "*                   ... please wait                           *"
echo "*                                                             *"
echo "***************************************************************"

#sleep 2

#apt-get update
#apt-get install -y dialog git

# todo check is current docker-ce installed?
if dialog --stdout --title "Need to install latest DOCKER?" \
          --backtitle "Install AllSky.py" \
          --yesno "If you have clear Debian and dont know anything about 'docker', just answer Yes" 7 60; then

	# remove old docker if exists
	apt-get remove docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc

	# install docker-ce + docker-compose
	apt-get update
	apt-get install ca-certificates curl gnupg
	install -m 0755 -d /etc/apt/keyrings
	curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
	chmod a+r /etc/apt/keyrings/docker.gpg

	echo \
	  "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
	  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
	  tee /etc/apt/sources.list.d/docker.list > /dev/null
	apt-get update

	apt-get install docker-ce docker-ce-cli containerd.io docker-compose-plugin
fi

if ! [ -f /opt/allsky.py/install.sh ] ; then
	cd /opt
	git clone https://github.com/oleg-milantiev/allsky.py.git
fi

exit

if [ "$INSTALL_GIT_CODE" = "yes" ]; then
	clear
	echo "***************************************************************"
	echo "*                                                             *"
	echo "*            INSTALLING allsky.py by Oleg Milantiev           *"
	echo "*       https://github.com/oleg-milantiev/allsky.py/wiki      *"
	echo "*                                                             *"
	echo "*                 Installing source code                      *"
	echo "*                                                             *"
	echo "***************************************************************"

	cd /opt
	git clone https://github.com/oleg-milantiev/allsky.py.git
fi

# docker pull
clear
echo "***************************************************************"
echo "*                                                             *"
echo "*            INSTALLING allsky.py by Oleg Milantiev           *"
echo "*       https://github.com/oleg-milantiev/allsky.py/wiki      *"
echo "*                                                             *"
echo "*                 Downloading docker images                   *"
echo "*                                                             *"
echo "***************************************************************"

cd /opt/allsky.py
docker compose pull

# composer install php libs
clear
echo "***************************************************************"
echo "*                                                             *"
echo "*            INSTALLING allsky.py by Oleg Milantiev           *"
echo "*       https://github.com/oleg-milantiev/allsky.py/wiki      *"
echo "*                                                             *"
echo "*                 Installing PHP libraries                    *"
echo "*                                                             *"
echo "***************************************************************"

docker run --env-file=.env --rm -it -v /opt/allsky.py:/opt/allsky.py \
  -w /opt/allsky.py olegmilantiev/allsky-php composer update

# start project
clear
echo "***************************************************************"
echo "*                                                             *"
echo "*            INSTALLING allsky.py by Oleg Milantiev           *"
echo "*       https://github.com/oleg-milantiev/allsky.py/wiki      *"
echo "*                                                             *"
echo "*                      Starting project                       *"
echo "*                                                             *"
echo "***************************************************************"
docker compose up -d
