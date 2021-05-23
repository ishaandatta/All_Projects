

sudo ls

qivFes-kivhup-ryxcu7

echo fa20-cs425-g22-01.cs.illinois.edu coordinator | sudo tee -a  /etc/hosts > /dev/null
echo fa20-cs425-g22-02.cs.illinois.edu worker1 | sudo tee -a  /etc/hosts > /dev/null
echo fa20-cs425-g22-03.cs.illinois.edu worker2 | sudo tee -a  /etc/hosts > /dev/null
echo fa20-cs425-g22-04.cs.illinois.edu worker3 | sudo tee -a  /etc/hosts > /dev/null
echo fa20-cs425-g22-05.cs.illinois.edu worker4 | sudo tee -a  /etc/hosts > /dev/null
echo fa20-cs425-g22-06.cs.illinois.edu worker5 | sudo tee -a  /etc/hosts > /dev/null
echo fa20-cs425-g22-07.cs.illinois.edu worker6 | sudo tee -a  /etc/hosts > /dev/null
echo fa20-cs425-g22-08.cs.illinois.edu worker7 | sudo tee -a  /etc/hosts > /dev/null
echo fa20-cs425-g22-09.cs.illinois.edu worker8 | sudo tee -a  /etc/hosts > /dev/null
echo fa20-cs425-g22-10.cs.illinois.edu worker9 | sudo tee -a  /etc/hosts > /dev/null


echo '
#HADOOP VARIABLES START
export HADOOP_PREFIX=/home/darciap2/hadoop
export HADOOP_HOME=/home/darciap2/hadoop
export HADOOP_CONF_DIR=${HADOOP_HOME}/etc/hadoop
export JAVA_HOME=/usr/lib/jvm/java-7-oracle
export PATH=$PATH:$HADOOP_PREFIX/bin
export PATH=$PATH:$HADOOP_PREFIX/sbin
export HADOOP_MAPRED_HOME=${HADOOP_HOME}
export HADOOP_COMMON_HOME=${HADOOP_HOME}
export HADOOP_HDFS_HOME=${HADOOP_HOME}
export YARN_HOME=${HADOOP_HOME}
export HADOOP_COMMON_LIB_NATIVE_DIR=${HADOOP_PREFIX}/lib/native
export HADOOP_OPTS="-Djava.library.path=${HADOOP_PREFIX}/lib/native"
export HADOOP_CLASSPATH=$JAVA_HOME/lib/tools.jar
#HADOOP VARIABLES END
' >> ~/.bashrc; source ~/.bashrc; echo $HADOOP_CONF_DIR


wget https://downloads.apache.org/hadoop/common/hadoop-2.10.1/hadoop-2.10.1.tar.gz
tar -xzvf ./hadoop-2.10.1.tar.gz
mv hadoop-2.10.1 hadoop
mkdir ~/hdfstmp

echo '
#HADOOP VARIABLES START
export HADOOP_PREFIX=/home/darciap2/hadoop
export HADOOP_HOME=/home/darciap2/hadoop
#HADOOP VARIABLES END
' >> ~/.bashrc; source ~/.bashrc


echo '<configuration>

<property>
<name>hadoop.tmp.dir</name>
  <value>/home/darciap2/hdfstmp</value>
</property>

<property>
  <name>fs.default.name</name>
  <value>hdfs://coordinator:8020</value>
</property>

<property>
    <name>fs.defaultFS</name>
    <value>hdfs://coordinator:8020</value>
</property>

</configuration>' > $HADOOP_CONF_DIR/core-site.xml



echo '<configuration>
<property>
  <name>dfs.replication</name>
  <value>2</value>
</property>

<property>
  <name>dfs.permissions</name>
  <value>false</value>
</property>

<property>
  <name>fs.default.name</name>
  <value>hdfs://coordinator:8020</value>
</property>

<property>
  <name>dfs.data.dir</name>
  <value>/home/darciap2/hdfstmp/dfs/name/data</value>
  <final>true</final>
</property>
<property>
  <name>dfs.name.dir</name>
  <value>/home/darciap2/hdfstmp/dfs/name</value>
  <final>true</final>
</property>

</configuration>' > $HADOOP_CONF_DIR/hdfs-site.xml


echo '<configuration>
<property>
  <name>mapred.job.tracker</name>
  <value>hdfs://hadoopmaster:8021</value>
</property>
<property>
  <name>mapreduce.framework.name</name>
  <value>yarn</value>
</property>
</configuration>' > $HADOOP_CONF_DIR/mapred-site.xml


echo '<configuration>

  <property>
    <name>yarn.resourcemanager.hostname</name>
    <value>coordinator</value>
  </property>

  <property>
    <name>yarn.nodemanager.aux-services</name>
    <value>mapreduce_shuffle</value>
  </property>
 
  <property>
    <name>yarn.nodemanager.aux-services.mapreduce_shuffle.class</name>
    <value>org.apache.hadoop.mapred.ShuffleHandler</value>
  </property>

</configuration>' > $HADOOP_CONF_DIR/yarn-site.xml

echo 'export JAVA_HOME=/usr/lib/jvm/java-7-oracle' > $HADOOP_CONF_DIR/hadoop-env.sh

echo 'worker1
worker2
worker3
worker4
worker5
worker6
worker7
worker8
worker9' > $HADOOP_CONF_DIR/slaves

echo '
#HADOOP VARIABLES START
export JAVA_HOME=/usr/lib/jvm/java-1.8.0-openjdk-1.8.0.272.b10-1.el7_9.x86_64/jre
export HADOOP_CLASSPATH=$JAVA_HOME/lib/tools.jar
#HADOOP VARIABLES END
' >> ~/.bashrc; source ~/.bashrc; echo $HADOOP_CONF_DIR

echo 'export JAVA_HOME=/usr/lib/jvm/java-1.8.0-openjdk-1.8.0.272.b10-1.el7_9.x86_64/jre' > $HADOOP_CONF_DIR/hadoop-env.sh


/usr/bin/java


# cat /etc/hosts
# Do not remove the following line, or various programs
# that require network functionality will fail.
127.0.0.1   localhost localhost.localdomain localhost4 localhost4.localdomain4
::1         localhost localhost.localdomain localhost6 localhost6.localdomain6
##############################################
# my cluster
###############################################
fa20-cs425-g22-01.cs.illinois.edu  coordinator
fa20-cs425-g22-02.cs.illinois.edu  worker1.hadoop.com worker1 
fa20-cs425-g22-03.cs.illinois.edu  worker2.hadoop.com worker2 
fa20-cs425-g22-04.cs.illinois.edu  worker3.hadoop.com worker3
fa20-cs425-g22-05.cs.illinois.edu  worker4.hadoop.com worker4 
fa20-cs425-g22-06.cs.illinois.edu  worker5.hadoop.com worker5 
fa20-cs425-g22-07.cs.illinois.edu  worker6.hadoop.com worker6 
fa20-cs425-g22-08.cs.illinois.edu  worker7.hadoop.com worker7 
fa20-cs425-g22-09.cs.illinois.edu  worker8.hadoop.com worker8 
fa20-cs425-g22-10.cs.illinois.edu  worker9.hadoop.com worker9 

sudo -- sh -c "
echo '# Do not remove the following line, or various programs
# that require network functionality will fail.
127.0.0.1   localhost localhost.localdomain localhost4 localhost4.localdomain4
::1         localhost localhost.localdomain localhost6 localhost6.localdomain6
##############################################
# my cluster
###############################################
fa20-cs425-g22-01.cs.illinois.edu  coordinator
fa20-cs425-g22-02.cs.illinois.edu  worker1.hadoop.com worker1 
fa20-cs425-g22-03.cs.illinois.edu  worker2.hadoop.com worker2 
fa20-cs425-g22-04.cs.illinois.edu  worker3.hadoop.com worker3
fa20-cs425-g22-05.cs.illinois.edu  worker4.hadoop.com worker4 
fa20-cs425-g22-06.cs.illinois.edu  worker5.hadoop.com worker5 
fa20-cs425-g22-07.cs.illinois.edu  worker6.hadoop.com worker6 
fa20-cs425-g22-08.cs.illinois.edu  worker7.hadoop.com worker7 
fa20-cs425-g22-09.cs.illinois.edu  worker8.hadoop.com worker8 
fa20-cs425-g22-10.cs.illinois.edu  worker9.hadoop.com worker9' > /etc/hosts
"