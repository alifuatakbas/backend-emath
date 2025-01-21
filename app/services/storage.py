import boto3
from fastapi import UploadFile
from uuid import uuid4
import os
from dotenv import load_dotenv

load_dotenv()


class S3Service:
    def __init__(self):
        try:
            # Environment variables'ları kontrol et
            access_key = os.getenv('AWS_ACCESS_KEY')
            secret_key = os.getenv('AWS_SECRET_KEY')
            bucket_name = os.getenv('AWS_BUCKET_NAME')
            region = os.getenv('AWS_REGION')

            print("AWS Credentials Check:", {
                "access_key": "✓" if access_key else "✗",
                "secret_key": "✓" if secret_key else "✗",
                "bucket_name": "✓" if bucket_name else "✗",
                "region": "✓" if region else "✗"
            })

            if not all([access_key, secret_key, bucket_name, region]):
                raise Exception("Missing AWS credentials")

            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region
            )
            self.bucket_name = bucket_name

        except Exception as e:
            print(f"S3 Error: {str(e)}")
            raise e

    async def upload_file(self, file: UploadFile) -> str:
        try:
            content = await file.read()
            file_extension = os.path.splitext(file.filename)[1]
            unique_filename = f"{uuid4()}{file_extension}"

            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=f"question_images/{unique_filename}",
                Body=content,
                ContentType=file.content_type,
                ACL='public-read'
            )

            url = f"https://{self.bucket_name}.s3.{os.getenv('AWS_REGION')}.amazonaws.com/question_images/{unique_filename}"
            return url

        except Exception as e:
            print(f"Upload Error: {str(e)}")
            return None