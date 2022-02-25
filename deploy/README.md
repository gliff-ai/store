You require the Azure CLI installed and authenticated

First create an Ignition file (machine readable config) from the Butane (human readable config).
This writes our docker-compose file, installs docker-compose, papertrail and mounts the remote HD on first boot.

We are limited to 3 VMs connected to each datadrive, so effectively, 3 vms per environment. 

Then we create the Azure VM, assign it an identity which has permission to access ACR and get our .env file. We attach the data drive too, which we mount when the ignition script runs.

For All Environments:
```bash
VM_NAME=machine1 # Change this
```

For Staging:

```bash
butane staging.bu --strict -o deploy.ign

AZ_IMAGE_NAME=fcos-stable # DON'T change these
SSH_KEY_NAME=storeStagingAdmin
RESOURCE_GROUP=gliff_staging
DISK_NAME=store-staging_etebase
STORAGE_ACCOUNT=staginggliff # Startup diagnostic logs go here
DISK_ID=$(az disk show -g $RESOURCE_GROUP -n $DISK_NAME --query 'id' -o tsv)

az vm create -n "${VM_NAME}" -g "${RESOURCE_GROUP}" \
   --image "${AZ_IMAGE_NAME}" \
   --admin-username core \
   --custom-data ./deploy.ign \
   --attach-data-disks $DISK_ID \
   --assign-identity vm_registry_access_store \
   --admin-username core \
   --ssh-key-name "${SSH_KEY_NAME}" \
   --boot-diagnostics-storage "${STORAGE_ACCOUNT}"
```

Add to the Application Gateway Backend Pool (TODO: Cli Command for this or Butane to self register)
Add to Azure pipeline (TODO: Butane for this?)
Remove port 22 access.

Ideally we'd use a Scaling Set for the VMs but this doesn't seem to support mounting a shared drive

