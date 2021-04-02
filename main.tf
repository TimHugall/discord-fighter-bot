resource "aws_dynamodb_table" "queue_table" {
  name         = "${var.env}-discord-fighter-bot-queue"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "Author"

  attribute {
    name = "Author"
    type = "S"
  }

}

resource "aws_iam_role" "lambda_role" {
  assume_role_policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Principal" : {
          "Service" : "lambda.amazonaws.com"
        },
        "Action" : "sts:AssumeRole"
      }
    ]
  })
  inline_policy {
    name = "${var.env}-bot-policy"
    policy = jsonencode({
      "Version" : "2012-10-17",
      "Statement" : [
        {
          "Effect" : "Allow",
          "Action" : [
            "dynamodb:*"
          ],
          "Resource" : "${aws_dynamodb_table.queue_table.arn}"
        },
        {
          "Effect" : "Allow",
          "Action" : [
            "ssm:*"
          ],
          "Resource" : "${aws_ssm_parameter.bot_token.arn}*"
        }
      ]
    })
  }
  managed_policy_arns = ["arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"]
}

resource "aws_cloudwatch_event_rule" "trigger_event" {
  name                = "${var.env}-discord-fighter-bot-trigger"
  schedule_expression = "rate(15 minutes)"
  is_enabled          = true
}

resource "aws_ssm_parameter" "bot_token" {
  name  = "${var.env}-discord-fighter-bot-token"
  type  = "SecureString"
  value = var.bot_token
}

resource "aws_lambda_function" "discord_bot" {
  depends_on = [
    aws_ssm_parameter.bot_token
  ]
  filename                       = "src/deployment-package.zip"
  handler                        = "main.lambda_handler"
  runtime                        = "python3.8"
  memory_size                    = 128
  timeout                        = var.env == "dev" ? 60 : 900
  role                           = aws_iam_role.lambda_role.arn
  source_code_hash               = length(var.source_code_hash) > 0 ? var.source_code_hash : filebase64sha256("src/deployment-package.zip")
  reserved_concurrent_executions = 1
  function_name                  = "${var.env}-discord-fighter-bot"
  environment {
    variables = {
      TableName = aws_dynamodb_table.queue_table.id
      Env       = var.env
    }
  }
}

resource "aws_cloudwatch_event_target" "trigger_target" {
  rule = aws_cloudwatch_event_rule.trigger_event.id
  arn  = aws_lambda_function.discord_bot.arn
}

resource "aws_lambda_permission" "invocation_policy" {
  action        = "lambda:InvokeFunction"
  source_arn    = aws_cloudwatch_event_rule.trigger_event.arn
  principal     = "events.amazonaws.com"
  function_name = aws_lambda_function.discord_bot.arn
}

output "source_code_hash" {
  value = aws_lambda_function.discord_bot.source_code_hash
}