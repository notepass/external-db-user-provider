# External DB suer provider
This repo contains a kubernetes resource to create DB users in external (or also internal, probably) databases
to automate DB user bootstrapping. It is currently compatible with postgres and mariadb/mysql.  
The provider itself is very minimalistic and might not fit your use case, so customisation might be necesarry.

## Setting it up
You will need to add the helm repository first via ``helm repo add db-user-provider https://notepass.github.io/external-db-user-provider``.
Then install the chart via: ``helm install external-db-user-provider db-user-provider/external-db-user-provider --namespace external-db-user-provider``.

The default configuration expects two secrets in the namespace the chart is deployed to:
- pg-admin-creds
- mariadb-admin-creds

Both should contain the fields ``username`` and ``password``. These store the users which will create the DB users.
Because of this, both those users will need superuser privileges.
This is also, why it is advisable to deploy this application to its own namespace.

The name of the secrets as well as the keys for username and password can be changed via the values file.
Just have a look at the default file as a reference, it is quite small.

## Using it
The provider comes with 2 CRDs: ``DbUserRequest`` and ``DbUser``. You will need to create a ``DbUserRequest``
object for each DB User you would like. This is then getting picked up by the controller, which will create
the according user and then create a secret with the generated username and password for the requested DB name.
Afterwards a DbUser object is created and the DbUserRequest object is deleted to show successful processing.

If a DbUser object already exists for the DbUserRequest object, the creation of any users or objects is skipped and
the DbUserRequest object is deleted.

If the secret which should be generated already exists, no user will be created and the according DbUser object will be created
before the request object is deleted.

This behaviour should make it safe to redeploy DbUserRequest objects for DbUsers that already exist. So this
controller should work with CI/CD tools like ArgoCD (which I am using).

**Note:** As the controller deletes DbUserRequest objects, do not use any "self-healing" options for things
like ArgoCD, as that would lead to a constant cycle of creation and deletion.

A DbUserRequest looks like this:
```yaml
apiVersion: notepass.de/v1
kind: DbUserRequest
metadata:
  name: db-user-test1
spec:
  db_type: postgres # or mariadb
  db_name: my_db_name # name of the DB to be created. Will also be used as the username
  secret_name: db-user-test1-secret # Secret to store the DB credentials into
  custom_db_name_prop: pgsql # Optional parameter: Will add a dbTypeCustom to the secret, see the information on the created secret for this to make more sense
```

This will create the following secret (Keys can currently not be renamed). The secret is created in the same namespace as the DbUserRequest.
```yaml
dbDb: my_db_name
dbHost: 127.0.0.1 # Will use the host value of the according DB type from the values file
dbPass: <24 alphanumerical character random password>
dbSchema: public # Only generated for posgres, always public
dbType: postgres # or mariadb
dbTypeAlt: postgresql # or mysql
dbTypeCustom: pgsql # Value from custom_db_name_prop in request. Field does not exist if not set in request
```

The generated DbUser object will look like this:
```yaml
Name:         db-user-test1
Namespace:    default # Whatever namespace the request was created in
Labels:       <none>
Annotations:  <none>
API Version:  notepass.de/v1
Kind:         DbUser
Spec:
  Created:      2025-11-26T15:22:00.686811+00:00 # Whenever the DbUserRequest was first fulfilled
  db_name:      my_db_name # Name of the created DB (Lowercase version of the given name)
  secret_name:  db-user-test1-secret # Name of the secret the credentials are stored in
Events:         <none>
```