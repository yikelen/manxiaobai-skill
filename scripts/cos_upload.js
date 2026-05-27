// COS 上传 — cos-nodejs-sdk-v5
const COS = require('cos-nodejs-sdk-v5');
const fs = require('fs');

const [file, key] = process.argv.slice(2);
const cos = new COS({
  SecretId: process.env.TENCENT_COS_SECRET_ID,
  SecretKey: process.env.TENCENT_COS_SECRET_KEY,
});

cos.putObject({
  Bucket: process.env.TENCENT_COS_BUCKET,
  Region: process.env.TENCENT_COS_REGION,
  Key: key,
  Body: fs.createReadStream(file),
}, (err, data) => {
  if (err) {
    console.error(err);
    process.exit(1);
  }
  const url = `https://${process.env.TENCENT_COS_BUCKET}.cos.${process.env.TENCENT_COS_REGION}.myqcloud.com/${key}`;
  console.log(url);
});
