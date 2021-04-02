terraform {
  backend "s3" {
    bucket = "hugall-terraform-state"
    key    = "dev/discord-fighter-bot.tfstate"
    region = "ap-southeast-2"
  }
}
