import boto3
from fastapi import UploadFile
from uuid import uuid4
import os
from dotenv import load_dotenv

load_dotenv()


class S3Service:
    def __init__(self):
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY'),
                aws_secret_access_key=os.getenv('AWS_SECRET_KEY'),
                region_name=os.getenv('AWS_REGION', 'eu-central-1')
            )
            self.bucket_name = os.getenv('AWS_BUCKET_NAME')
            print("AWS Credentials:", {
                "access_key": os.getenv('AWS_ACCESS_KEY')[:5] + "...",
                "bucket": self.bucket_name,
                "region": os.getenv('AWS_REGION')
            })
        except Exception as e:
            print(f"S3 initialization error: {str(e)}")
            raise e

    async def upload_file(self, file: UploadFile) -> str:
        try:
            file_extension = os.path.splitext(file.filename)[1]
            unique_filename = f"{uuid4()}{file_extension}"

            print(f"Uploading file: {file.filename} to {self.bucket_name}")

            self.s3_client.upload_fileobj(
                file.file,
                self.bucket_name,
                f"question_images/{unique_filename}",
                ExtraArgs={
                    'ACL': 'public-read',
                    'ContentType': file.content_type
                }
            )

            url = f"https://{self.bucket_name}.s3.amazonaws.com/question_images/{unique_filename}"
            print(f"Upload successful. URL: {url}")
            return url

        except Exception as e:
            print(f"S3 upload error: {str(e)}")
            return None