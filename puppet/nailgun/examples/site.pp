node default {

  Exec  {path => '/usr/bin:/bin:/usr/sbin:/sbin'}

  $centos_repos =
  [
   {
   "name" => "Nailgun",
   "url"  => "http://${ipaddress}:8080/centos/6.3/nailgun/x86_64"
   },
   ]
 
  $centos_iso = "file:///var/www/nailgun/iso/CentOS-6.3-x86_64-netinstall-EFI.iso"
  $cobbler_user = "cobbler"
  $cobbler_password = "cobbler"

  $puppet_master_hostname = "${hostname}.${domain}"
   
  $mco_pskey = "unset"
  $mco_stompuser = "mcollective"
  $mco_stomppassword = "marionette"

  $rabbitmq_naily_user = "naily"
  $rabbitmq_naily_password = "naily"
   
  $repo_root = "/var/www/nailgun"
  $pip_repo = "/var/www/nailgun/eggs"
  $gem_source = "http://localhost:8080/gems/"
                   
  
  class { "nailgun":
    package => "Nailgun",
    version => "0.1.0",
    naily_version => "0.1",
    nailgun_group => "nailgun",
    nailgun_user => "nailgun",
    venv => "/opt/nailgun",

    pip_index => "--no-index",
    pip_find_links => "-f file://${pip_repo}",
    gem_source => $gem_source,

    databasefile => "/var/tmp/nailgun.sqlite",
    staticdir => "/opt/nailgun/usr/share/nailgun/static",
    templatedir => "/opt/nailgun/usr/share/nailgun/static",
    logfile => "/var/tmp/nailgun.log",

    cobbler_url => "http://localhost/cobbler_api",
    cobbler_user => $cobbler_user,
    cobbler_password => $cobbler_password,

    mco_pskey => $mco_pskey,
    mco_stompuser => $mco_stompuser,
    mco_stomppassword => $mco_stomppassword,

    rabbitmq_naily_user => $rabbitmq_naily_user,
    rabbitmq_naily_password => $rabbitmq_naily_password,

    puppet_master_hostname => $puppet_master_hostname,
  }

}
