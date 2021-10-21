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

resource "google_pubsub_subscription" "iot_data_topic_subscription" {
  name = "iot-data-subsciption"
  topic = google_pubsub_topic.iot_data_topic.name
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