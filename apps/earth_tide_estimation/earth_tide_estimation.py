import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
import pygtide
import streamlit as st

st.subheader("Groundwater pressure dataset")
gw = st.file_uploader("Upload dataset", type=["csv"], key='gw')

st.subheader("Barometric pressure dataset")
bp = st.file_uploader("Upload dataset", type=["csv"], key='bp')

if (gw is not None)&(bp is not None):
    st.subheader("Download Earth tide coefficient values estimated by HALS")
    st.download_button("Download as CSV",  gw.to_csv().encode('utf-8'), "HALS_amps_and_phases.csv")
