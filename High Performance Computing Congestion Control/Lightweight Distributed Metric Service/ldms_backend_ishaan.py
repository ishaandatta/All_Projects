LDMS_CSV = '/home/jovyan/work/LDMS_parser/LDMS/metric_set_rtr_0_2_c.1545400200'
LDMS_HEADER = '/home/jovyan/work/LDMS_parser/LDMS/HEADER'
FLIT_REGEX = 'AR_RTR_\d_\d_INQ_PRF_INCOMING_FLIT_VC\d'
#nic_2_proc
#nic_2_hsn
NIC_CSV = '/home/jovyan/work/LDMS_parser/LDMS/metric_set_nic.1542700800'
NIC_HEADER = '/home/jovyan/work/LDMS_parser/LDMS/HEADER_NIC'
# FLIT_REGEX = 'AR_RTR_\d_\d_INQ_PRF_INCOMING_FLIT_VC\d'
NIC2PROC_FLIT_COL  = "AR_NIC_RSPMON_PARB_EVENT_CNTR_PI_FLITS" 
NIC2PROC_STALL_COL = "AR_NIC_RSPMON_PARB_EVENT_CNTR_PI_STALLED"
NIC2HSN_FLIT_COL  =  "AR_NIC_NETMON_ORB_EVENT_CNTR_REQ_FLITS"
NIC2HSN_STALL_COL = "AR_NIC_NETMON_ORB_EVENT_CNTR_REQ_STALLED"
NEW_FLIT_REGEX = 'AR_RTR_\d_\d_INQ_PRF_INCOMING_FLIT'
STALL_REGEX = 'AR_RTR_\d_\d_INQ_PRF_ROWBUS_STALL_CNT'
OUTPUT_CSV = 'output/processed.csv'

import pandas as pd
import dask.dataframe as dd

import re
from collections import OrderedDict
from operator import itemgetter
import time
import sys
import os
import numpy as np
import pyspark
from pyspark.sql import *
import matplotlib.pyplot as plt
import ipywidgets as widgets

def get_processed_df(aries_router_id,r,c,delta1,delta2):
    header = open(LDMS_HEADER).readlines()[0].strip().split(',')
#     with open(LDMS_CSV, "r") as f:
#         f.seek (0, 2)           # Seek @ EOF
#         fsize = f.tell()        # Get Size
#         f.seek (max (fsize-1024, 0), 0) # Set pos @ last n chars
#         lines = f.readlines()       # Read to end

#         lines = lines[-10:]    # Get last 10 lines
    df = pd.read_csv(LDMS_CSV)
    
    df.columns = header
    df['#Time'] = pd.to_numeric(df['#Time'])

    df = df.rename(columns={'#Time': 'time'})
    
    max_time = df['time'].max()
    df = df[(df['time']>=max_time-delta1)&(df['time']<=max_time-delta2)]
    df = df[df['aries_rtr_id']==aries_router_id]

    new_flit_rgx = 'AR_RTR_'+str(r)+'_'+str(c)+'_INQ_PRF_INCOMING_FLIT'
    stall_regex = 'AR_RTR_'+ str(r)+'_'+ str(c)+'_INQ_PRF_ROWBUS_STALL_CNT'

    sum_cols = [new_flit_rgx+'_VC'+str(vc) for vc in range(0,8)]
    drop_cols = sum_cols
    flit_val = df[sum_cols[0]]+df[sum_cols[1]]+\
                                       df[sum_cols[2]]+df[sum_cols[3]]\
                                       +df[sum_cols[4]]+df[sum_cols[5]]+\
                                       df[sum_cols[6]]+df[sum_cols[7]]
    stall_val = df[stall_regex]
    val = {'flit':flit_val, 'stall':stall_val}
    df_new = pd.DataFrame(data=val)
    df_new = df_new.sort_values(by = ['flit'])
    df_out =  df_new - df_new.shift(1)
    df_out = df_out.dropna()
    df_out = df_out.reindex()
    df_out = df_out.reset_index(drop=True)
    df_out['time'] = pd.Series([i for i in range(0,len(df_out))])
    return df_out

def get_processed_df_nic2proc(aries_router_id,r,c,delta1,delta2):
    header = open(NIC_HEADER).readlines()[0].strip().split(',')
    
    df = pd.read_csv(NIC_CSV)
    
    df.columns = header
    df['#Time'] = pd.to_numeric(df['#Time'])

    df = df.rename(columns={'#Time': 'time'})
    
    max_time = df['time'].max()
    df = df[(df['time']>=max_time-delta1)&(df['time']<=max_time-delta2)]
    df = df[df['aries_rtr_id']==aries_router_id]

#     new_flit_rgx = 'AR_RTR_'+str(r)+'_'+str(c)+'_INQ_PRF_INCOMING_FLIT'
#     stall_regex = 'AR_RTR_'+ str(r)+'_'+ str(c)+'_INQ_PRF_ROWBUS_STALL_CNT'

#     sum_cols = [new_flit_rgx+'_VC'+str(vc) for vc in range(0,8)]
#     drop_cols = sum_cols
#     flit_val = df[sum_cols[0]]+df[sum_cols[1]]+\
#                                        df[sum_cols[2]]+df[sum_cols[3]]\
#                                        +df[sum_cols[4]]+df[sum_cols[5]]+\
#                                        df[sum_cols[6]]+df[sum_cols[7]]
    flit_val = df[NIC2PROC_FLIT_COL]
    stall_val = df[NIC2PROC_STALL_COL]
    val = {'flit':flit_val, 'stall':stall_val}
    df_new = pd.DataFrame(data=val)
    df_new = df_new.sort_values(by = ['flit'])
    df_out =  df_new - df_new.shift(1)
    df_out = df_out.dropna()
    df_out = df_out.reindex()
    df_out = df_out.reset_index(drop=True)
    df_out['time'] = pd.Series([i for i in range(0,len(df_out))])
    return df_out

def get_processed_df_nic2hsn(aries_router_id,r,c,delta1,delta2):
    
    header = open(NIC_HEADER).readlines()[0].strip().split(',')
    df = pd.read_csv(NIC_CSV)
    
    df.columns = header
    df['#Time'] = pd.to_numeric(df['#Time'])
    df = df.rename(columns={'#Time': 'time'})
    
    max_time = df['time'].max()
    df = df[(df['time']>=max_time-delta1)&(df['time']<=max_time-delta2)]
    df = df[df['aries_rtr_id']==aries_router_id]

    flit_val = df[NIC2HSN_FLIT_COL]
    stall_val = df[NIC2HSN_STALL_COL]
    val = {'flit':flit_val, 'stall':stall_val}
    df_new = pd.DataFrame(data=val)
    df_new = df_new.sort_values(by = ['flit'])
    df_out =  df_new - df_new.shift(1)
    df_out = df_out.dropna()
    df_out = df_out.reindex()
    df_out = df_out.reset_index(drop=True)
    df_out['time'] = pd.Series([i for i in range(0,len(df_out))])
    return df_out
