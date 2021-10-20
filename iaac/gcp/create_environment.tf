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