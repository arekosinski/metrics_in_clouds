variable "gcp_project_name" {
  type        = string
  description = "Default project name"
  default     = "data-integration-playground"
}

provider "google" {
  project = var.gcp_project_name
  region  = "europe-west3"
  zone    = "europe-west3-a"
}

resource "google_service_account" "pubsub_sa" {
  account_id   = "pubsub-integration"
  display_name = "SA for PubSub integration"
}

resource "google_pubsub_topic" "iot_data_topic" {
  name = "iot-data"
}

resource "google_pubsub_topic_iam_policy" "pubsub_publish_permissions" {
  project = google_pubsub_topic.iot_data_topic.project
  topic = google_pubsub_topic.iot_data_topic.name
  policy_data = data.google_iam_policy.pubsub_publisher.policy_data
}

data "google_iam_policy" "pubsub_publisher" {
  binding {
    role = "roles/pubsub.publisher"
    members = [ format("serviceAccount:%s",google_service_account.pubsub_sa.email) ]
  }
}

resource "google_bigquery_dataset" "bq_iot_dataset" {
  dataset_id                  = "iot_data"
  friendly_name               = "iot_data"
  location                    = "EU"
}

resource "google_bigquery_dataset_iam_member" "sa_grant_editor" {
  dataset_id = google_bigquery_dataset.bq_iot_dataset.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.pubsub_sa.email}"
}

resource "google_bigquery_table" "iot_base_table" {
  dataset_id = google_bigquery_dataset.bq_iot_dataset.dataset_id
  table_id   = "iot_base_data"

  time_partitioning {
    type = "DAY"
    require_partition_filter = true
    field = "event_timestamp"
  }

  clustering = ["device_id","measure_name"]

  schema = <<EOF
  [{
    "name": "event_timestamp",
    "type": "TIMESTAMP",
    "mode": "NULLABLE",
    "description": "event generation time"
  },
  {
    "name": "device_id",
    "type": "STRING",
    "mode": "NULLABLE",
    "description": "Device identification number"
  },
  {
    "name": "measure_code",
    "type": "STRING",
    "mode": "NULLABLE",
    "description": "Measure code - short version"
  },
  {
    "name": "measure_name",
    "type": "STRING",
    "mode": "NULLABLE",
    "description": "Measure code - long version"
  },
  {
    "name": "measure_value",
    "type": "NUMERIC",
    "mode": "NULLABLE",
    "description": "Measurment taken by device for measure code"
  },
  {
    "name": "cycle_number",
    "type": "INTEGER",
    "mode": "NULLABLE",
    "description": "Measurment taken by device for measure code"
  },
  {
    "name": "version",
    "type": "INTEGER",
    "mode": "NULLABLE",
    "description": "Measurment taken by device for measure code"
  }]
EOF
}

resource "google_storage_bucket" "gs_cf_bucket" {
  name = "iot_data_deployment"
  location = "europe-central2"
  force_destroy = true
  requester_pays = true
  uniform_bucket_level_access = true
}

resource "google_storage_bucket_iam_member" "gs_cf_bucket_owner" {
  bucket = google_storage_bucket.gs_cf_bucket.name
  role = "roles/storage.admin"
  member = "serviceAccount:${google_service_account.pubsub_sa.email}"
}

resource "google_storage_bucket_object" "cf_code" {
  name   = "cf_iot_data.zip"
  bucket = google_storage_bucket.gs_cf_bucket.name
  source = "../../build/cf_iot_data.zip"
}

resource "google_cloudfunctions_function" "cf_pubsub_to_bigquery" {
  name        = "cf-iot-pubsub-to-bigquery"
  description = "publish data from pubsub queue to bigquery tables"
  runtime     = "python37"
  available_memory_mb = 256
  timeout = 60
  entry_point = "pubsub_to_bigq"
  event_trigger {
    event_type = "google.pubsub.topic.publish"
    resource = "projects/${var.gcp_project_name}/topics/${google_pubsub_topic.iot_data_topic.name}"
  }
  ingress_settings = "ALLOW_INTERNAL_ONLY"
  max_instances = 3
  # service_account_email = google_service_account.pubsub_sa.email
  environment_variables = {
    ENV_BQ_TABLE = "iot_base_data",
    ENV_BQ_DATASET = "iot_data",
    ENV_DEBUG = "1"
  } 
  source_archive_bucket = google_storage_bucket.gs_cf_bucket.name
  source_archive_object = google_storage_bucket_object.cf_code.name 

  depends_on = [
    google_storage_bucket_object.cf_code
  ]
}