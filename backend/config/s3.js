const AWS = require("aws-sdk");

AWS.config.update({
  accessKeyId: process.env.AWS_ACCESS_KEY,
  secretAccessKey: process.env.AWS_SECRET_KEY,
  region: process.env.AWS_REGION,
});

const s3 = new AWS.S3({
  signatureVersion: 'v4',
  httpOptions: {
    timeout: 300000, // 5 minutes
    connectTimeout: 10000
  }
});

module.exports = s3;