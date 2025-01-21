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
                region_name=os.getenv('AWS_REGION')
            )
            self.bucket_name = os.getenv('AWS_BUCKET_NAME')

            # Test connection
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            print("Successfully connected to S3")

        except Exception as e:
            print(f"S3 Error: {str(e)}")
            raise e

    async def upload_file(self, file: UploadFile) -> str:
        try:
            content = await file.read()
            file_extension = os.path.splitext(file.filename)[1]
            unique_filename = f"{uuid4()}{file_extension}"

            print(f"Attempting to upload {unique_filename} to {self.bucket_name}")

            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=f"question_images/{unique_filename}",
                Body=content,
                ContentType=file.content_type,
                ACL='public-read'
            )

            url = f"https://{self.bucket_name}.s3.{os.getenv('AWS_REGION')}.amazonaws.com/question_images/{unique_filename}"
            print(f"Successfully uploaded. URL: {url}")
            return url

        except Exception as e:
            print(f"Upload Error: {str(e)}")
            return None