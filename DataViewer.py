import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import numpy as np

import streamlit.components.v1 as components

# --- Helper Functions ---
def get_db_connection(db_path):
    try:
        conn = sqlite3.connect(db_path, check_same_thread=False)
        return conn
    except Exception as e:
        st.error(f"Error connecting to database: {e}")
        return None

def get_table_names(conn):
    try:
        query = "SELECT name FROM sqlite_master WHERE type='table' AND name!='sqlite_sequence'"
        return pd.read_sql_query(query, conn)
    except Exception as e:
        st.error(f"Error getting table names: {e}")
        return pd.DataFrame()

def get_table_data(conn, table_name):
    try:
        pragma_query = f"PRAGMA table_info(`{table_name}`)"
        schema_df = pd.read_sql_query(pragma_query, conn)
        dtype_map = {}
        string_types = ['TEXT', 'VARCHAR', 'CHAR', 'CLOB']
        for index, row in schema_df.iterrows():
            col_name = row['name']
            col_type = str(row['type']).upper()
            if any(st in col_type for st in string_types):
                dtype_map[col_name] = 'string'
        return pd.read_sql_query(f"SELECT * FROM `{table_name}`", conn, dtype=dtype_map)
    except Exception as e:
        st.error(f"Error getting table data: {e}")
        return pd.DataFrame()

def display_plot(df, columns, key_prefix):
    x_axis = st.selectbox("X-axis", options=columns, key=f"{key_prefix}_x_axis")
    y_axes = st.multiselect("Y-axes", options=[c for c in columns if c != x_axis], key=f"{key_prefix}_y_axes")

    with st.expander("Customize Plot"):
        plot_type = st.selectbox("Plot Type", ['Line', 'Bar', 'Scatter'], key=f"{key_prefix}_plot_type")
        if plot_type == 'Scatter' and len(y_axes) > 1:
            st.warning("Scatter plot only supports one Y-axis. Only the first selected Y-axis will be used.")
        color_by = st.selectbox("Color by", options=[None] + columns, key=f"{key_prefix}_color")
        symbol_by = st.selectbox("Symbol by", options=[None] + columns, key=f"{key_prefix}_symbol")
        if plot_type == 'Line':
            st.checkbox("Show Markers", key=f"{key_prefix}_markers")
        elif plot_type == 'Bar':
            st.radio("Bar Mode", ['group', 'relative'], key=f"{key_prefix}_barmode")
        elif plot_type == 'Scatter':
            st.selectbox("Size by", options=[None] + [c for c in columns if pd.api.types.is_numeric_dtype(df[c])],
                         key=f"{key_prefix}_size")
        st.checkbox("Use raw time format", key=f"{key_prefix}_plot_force_use_raw_time_format")


    with st.expander("Annotate & Modify Plot"):
        title_input = st.text_input("Plot Title", key=f"{key_prefix}_title_input")
        x_label_input = st.text_input("X-axis Label", key=f"{key_prefix}_xlabel_input")
        y_label_input = st.text_input("Y-axis Label", key=f"{key_prefix}_ylabel_input")
        legend_title_input = st.text_input("Legend Title", key=f"{key_prefix}_legend_title_input")
        st.checkbox("Show Values on Plot", key=f"{key_prefix}_show_values")
        new_legend_names = {}
        plot_type_for_legend = st.session_state.get(f"{key_prefix}_plot_type", 'Line')
        if plot_type_for_legend in ['Line', 'Bar'] and len(y_axes) > 1:
            st.markdown("---")
            st.write("Rename Legend Entries:")
            for col in y_axes:
                new_name = st.text_input(f'"{col}" ->', value=col, key=f"{key_prefix}_legend_{col}")
                new_legend_names[col] = new_name

    if x_axis and y_axes:
        try:
            plot_df = df.copy()
            if pd.api.types.is_period_dtype(plot_df[x_axis].dtype):
                # plot_df[x_axis] = plot_df[x_axis].to_timestamp()
                # plot_df[x_axis] = plot_df[x_axis].astype('datetime64[ns]')
                plot_df[x_axis] = plot_df[x_axis].astype('str')
                # print(type(plot_df[x_axis][0]))
                # pass
            for y_axis in y_axes:
                if pd.api.types.is_period_dtype(plot_df[y_axis].dtype):
                    # plot_df[y_axis] = plot_df[y_axis].to_timestamp()
                    # plot_df[y_axis] = plot_df[y_axis].astype('datetime64[ns]')
                    plot_df[y_axis] = plot_df[y_axis].astype('str')

            # print(plot_df.head(3))
            plot_type = st.session_state.get(f"{key_prefix}_plot_type", 'Line')
            show_values = st.session_state.get(f"{key_prefix}_show_values", False)
            fig = None
            if plot_type == 'Line':
                fig = px.line(plot_df, x=x_axis, y=y_axes, markers=st.session_state.get(f"{key_prefix}_markers", False),
                              color=st.session_state.get(f"{key_prefix}_color"),
                              symbol=st.session_state.get(f"{key_prefix}_symbol"))
            elif plot_type == 'Bar':
                fig = px.bar(plot_df, x=x_axis, y=y_axes, barmode=st.session_state.get(f"{key_prefix}_barmode", 'group'),
                             color=st.session_state.get(f"{key_prefix}_color"))
            elif plot_type == 'Scatter':
                fig = px.scatter(plot_df, x=x_axis, y=y_axes[0], color=st.session_state.get(f"{key_prefix}_color"),
                                 size=st.session_state.get(f"{key_prefix}_size"),
                                 symbol=st.session_state.get(f"{key_prefix}_symbol"))
            if fig:
                if show_values:
                    text_template = '%{y}'
                    if plot_type == 'Bar':
                        fig.update_traces(texttemplate=text_template, textposition='outside')
                    elif plot_type == 'Line':
                        mode = 'lines+text'
                        if st.session_state.get(f"{key_prefix}_markers", False):
                            mode = 'lines+markers+text'
                        fig.update_traces(texttemplate=text_template, textposition='top center', mode=mode)
                    elif plot_type == 'Scatter':
                        fig.update_traces(texttemplate=text_template, textposition='top center', mode='markers+text')

                fig.update_layout(
                    title_text=title_input if title_input else '',
                    xaxis_title=x_label_input if x_label_input else x_axis,
                    yaxis_title=y_label_input if y_label_input else (y_axes[0] if len(y_axes) == 1 else "Value"),
                    legend_title_text=legend_title_input if legend_title_input else None,
                    title_x=0.5,
                    title_xanchor='center'
                )
                if new_legend_names:
                    fig.for_each_trace(lambda t: t.update(name=new_legend_names.get(t.name, t.name)))

                if st.session_state.get(f"{key_prefix}_plot_force_use_raw_time_format", False):
                    fig.update_xaxes(type='category')  # Force categorical, not datetime
                st.plotly_chart(fig, width='stretch', config={'toImageButtonOptions': {'scale': 3}})
        except Exception as e:
            st.error(f"Error plotting: {e}")

def main(mode):
    st.set_page_config(layout="wide", page_title="Data Viewer")

    st.title("Data Viewer and Analyzer")

    # --- Initialize Session State ---
    if "data_df" not in st.session_state:
        st.session_state.data_df = None
    if "cleaned_df" not in st.session_state:
        st.session_state.cleaned_df = None
    if "uploaded_filename" not in st.session_state:
        st.session_state.uploaded_filename = None
    if "uploaded_file_obj" not in st.session_state:
        st.session_state.uploaded_file_obj = None
    if "show_clear_message" not in st.session_state:
        st.session_state.show_clear_message = False
    if "is_time_series" not in st.session_state:
        st.session_state.is_time_series = False
    if "time_series_col" not in st.session_state:
        st.session_state.time_series_col = None
    if "time_series_period" not in st.session_state:
        st.session_state.time_series_period = None

    # Display clear message if flag is set
    if st.session_state.show_clear_message:
        st.sidebar.warning("User data has been completed destroyed.")
        st.session_state.show_clear_message = False

    st.sidebar.header("Data Source")

    # --- SERVER MODE ---
    if mode == 'server':
        # STATE 1: If data is loaded, show status and a clear button
        if st.session_state.data_df is not None:
            st.sidebar.success(f"Loaded: {st.session_state.uploaded_filename}")
            if st.sidebar.button("Clear Data", type="primary"):
                st.session_state.data_df = None
                st.session_state.cleaned_df = None
                st.session_state.uploaded_file_obj = None
                st.session_state.uploaded_filename = None
                st.session_state.show_clear_message = True
                st.rerun()

        # STATE 2: If a file has been uploaded (and not cleared), show load options
        if st.session_state.uploaded_file_obj is not None:
            try:
                header_row = st.sidebar.number_input("Header Row", min_value=0, value=0, help="The row number (0-indexed) to use as the column headers.")

                file_extension = st.session_state.uploaded_filename.split('.')[-1].lower()
                if file_extension in ["xlsx", "xls", "xlsm"]:
                    xls = pd.ExcelFile(st.session_state.uploaded_file_obj)
                    sheet_names = xls.sheet_names
                    selected_sheet = st.sidebar.selectbox("Select a sheet to load", sheet_names)

                if st.sidebar.button("Load Data", type="secondary"):
                    st.session_state.uploaded_file_obj.seek(0)
                    if file_extension == "csv":
                        st.session_state.data_df = pd.read_csv(st.session_state.uploaded_file_obj, header=header_row)
                    elif file_extension in ["xlsx", "xls", "xlsm"]:
                        st.session_state.data_df = pd.read_excel(st.session_state.uploaded_file_obj, sheet_name=selected_sheet, header=header_row)
                    
                    st.session_state.data_df = st.session_state.data_df.replace(r'^\s*$', np.nan, regex=True)
                    st.session_state.cleaned_df = None
                    if st.session_state.is_time_series:
                        st.session_state.is_time_series = False
                        st.session_state.time_series_col_selector = None
                        st.session_state.time_series_period_selector = None


                    st.rerun()

            except Exception as e:
                st.sidebar.error(f"Error processing file: {e}")
                st.session_state.uploaded_file_obj = None
                st.session_state.uploaded_filename = None
                st.rerun()

        # STATE 3: If no file is uploaded (and no file is pending options selection), show the uploader
        elif st.session_state.data_df is None and st.session_state.uploaded_file_obj is None:
            uploaded_file = st.sidebar.file_uploader("Choose a file", type=["csv", "xlsx", "xlsm", "xls"])

            if uploaded_file is not None:
                st.session_state.uploaded_filename = uploaded_file.name
                st.session_state.uploaded_file_obj = uploaded_file
                st.rerun()

    # --- LOCAL MODE ---
    else:
        if st.session_state.get('db_conn') is None and st.session_state.get('csv_path') is None and st.session_state.get('excel_path') is None:
            path_input = st.sidebar.text_input("Enter path to SQLite, CSV, or Excel file")
            if st.sidebar.button("Load Data"):
                file_extension = path_input.split('.')[-1].lower()
                if file_extension == 'db' or file_extension == 'sqlite' or file_extension == 'sqlite3':
                    st.session_state.db_conn = get_db_connection(path_input)
                    st.session_state.cleaned_df = None
                    st.rerun()
                elif file_extension == 'csv':
                    st.session_state.csv_path = path_input
                    st.rerun()
                elif file_extension in ['xlsx', 'xls', 'xlsm']:
                    st.session_state.excel_path = path_input
                    st.rerun()

        if st.session_state.get('db_conn') is not None:
            st.sidebar.success("Connected to database.")
            tables_df = get_table_names(st.session_state.db_conn)
            if not tables_df.empty:
                table_names = tables_df["name"].tolist()
                selected_table = st.sidebar.selectbox("Select a table", table_names)
                if st.sidebar.button("Load Table", type="secondary"):
                    st.session_state.data_df = get_table_data(st.session_state.db_conn, selected_table)
                    st.session_state.data_df = st.session_state.data_df.replace(r'^\s*$', np.nan, regex=True)
                    st.session_state.cleaned_df = None
                    st.rerun()

            if st.sidebar.button("Close Connection", type="primary"):
                st.session_state.db_conn.close()
                st.session_state.db_conn = None
                st.session_state.data_df = None
                st.session_state.cleaned_df = None
                st.rerun()

        if st.session_state.get('csv_path') is not None:
            st.sidebar.success(f"Loaded: {st.session_state.csv_path}")
            header_row = st.sidebar.number_input("Header Row", min_value=0, value=0, help="The row number (0-indexed) to use as the column headers.")
            if st.sidebar.button("Load Data", type="secondary"):
                try:
                    st.session_state.data_df = pd.read_csv(st.session_state.csv_path, header=header_row)
                    st.session_state.data_df = st.session_state.data_df.replace(r'^\s*$', np.nan, regex=True)
                    st.session_state.cleaned_df = None
                    st.rerun()
                except FileNotFoundError:
                    st.sidebar.error("File not found. Please check the path.")
                except Exception as e:
                    st.sidebar.error(f"Error loading CSV: {e}")

            if st.sidebar.button("Close CSV", type="primary"):
                st.session_state.csv_path = None
                st.session_state.data_df = None
                st.session_state.cleaned_df = None
                st.rerun()

        if st.session_state.get('excel_path') is not None:
            st.sidebar.success(f"Opened: {st.session_state.excel_path}")
            try:
                xls = pd.ExcelFile(st.session_state.excel_path)
                sheet_names = xls.sheet_names
                selected_sheet = st.sidebar.selectbox("Select a sheet", sheet_names)
                header_row = st.sidebar.number_input("Header Row", min_value=0, value=0, help="The row number (0-indexed) to use as the column headers.")
                if st.sidebar.button("Load Data", type="secondary"):
                    st.session_state.data_df = pd.read_excel(st.session_state.excel_path, sheet_name=selected_sheet, header=header_row)
                    st.session_state.data_df = st.session_state.data_df.replace(r'^\s*$', np.nan, regex=True)
                    st.session_state.cleaned_df = None
                    st.rerun()
            except Exception as e:
                st.sidebar.error(f"Error processing Excel file: {e}")

            if st.sidebar.button("Close Excel", type="primary"):
                st.session_state.excel_path = None
                st.session_state.data_df = None
                st.session_state.cleaned_df = None
                st.rerun()

    # --- Main App ---
    if st.session_state.data_df is not None and not st.session_state.data_df.empty:
        data_df = st.session_state.data_df
        if 'id' in data_df.columns:
            data_df = data_df.drop(columns=['id'])

        st.sidebar.subheader("Loaded Data Columns")
        st.sidebar.dataframe(data_df.dtypes.astype(str).rename_axis(None).reset_index().rename(columns={'index': 'column', 0: 'dtype'}))

        is_time_series = st.sidebar.checkbox("Time Series Data", key="is_time_series")
        if is_time_series:
            time_series_col = st.sidebar.selectbox("Select the time series column", st.session_state.data_df.columns, key="time_series_col_selector")
            time_series_period = st.sidebar.selectbox("Select the time series period",["Daily", "Monthly", "Quarterly", "Yearly"], key="time_series_period_selector")
            period_dict = {"Daily":"D", "Monthly":"M", "Quarterly":"Q", "Yearly":"Y"}

            def on_apply_clicked():
                # st.session_state.time_series_col = st.session_state.time_series_col_selector
                # st.session_state.time_series_period = st.session_state.time_series_period_selector
                if st.session_state.time_series_col_selector and st.session_state.time_series_period_selector:
                    try:
                        st.session_state.data_df[st.session_state.time_series_col_selector] = pd.PeriodIndex(st.session_state.data_df[st.session_state.time_series_col_selector],
                                                                                                             freq=period_dict[st.session_state.time_series_period_selector])
                    except Exception as e:
                        print(f"Cannot convert column {st.session_state.time_series_col_selector} to period type of {st.session_state.time_series_period_selector}")
                        st.toast(f"Failed to convert column {st.session_state.time_series_col_selector} to proper time type internally, it will be treat as normal string.")

            st.sidebar.button('Apply', on_click=on_apply_clicked)

        tab1, tab2, tab3, tab4, tab5 = st.tabs(["Data View", "Column Analysis", "Filter & Plot", "Pivot Table", "Data Cleaning"])

        with tab1:
            st.header("Data View")
            st.dataframe(data_df)
            st.subheader("Data Summary")
            st.write(data_df.describe())

        with tab2:
            st.header("Column Analysis")

            all_columns = data_df.columns.tolist()
            columns_to_analyze = st.multiselect(
                "Select one or more columns to analyze",
                options=all_columns,
                key="column_analysis_selection"
            )

            if not columns_to_analyze:
                st.info("Please select one or more columns to begin analysis.")

            elif len(columns_to_analyze) == 1:
                st.subheader("Single Column Analysis")
                column_to_analyze = columns_to_analyze[0]
                col_data = data_df[column_to_analyze]
                is_numeric = pd.api.types.is_numeric_dtype(col_data)

                if is_numeric:
                    analysis_options = ['Value Plot', 'Histogram', 'Box Plot', 'Summary Statistics']
                else:
                    analysis_options = ['Value Plot', 'Value Counts', 'Summary Statistics']

                analysis_type = st.selectbox(
                    "Choose an analysis type",
                    options=analysis_options,
                    key="column_analysis_type"
                )

                st.subheader(f"Analysis of: `{column_to_analyze}`")

                if analysis_type == 'Summary Statistics':
                    st.write(col_data.describe())

                elif analysis_type == 'Histogram':
                    if is_numeric:
                        st.markdown("#### Histogram Parameters")
                        nbins = st.slider("Number of bins", min_value=5, max_value=100, value=30, key="hist_bins")
                        fig = px.histogram(data_df, x=column_to_analyze, nbins=nbins,
                                           title=f"Histogram of {column_to_analyze}")
                        st.plotly_chart(fig, width='stretch', config={'toImageButtonOptions': {'scale': 3}})
                    else:
                        st.warning("Histogram is only available for numeric columns.")

                elif analysis_type == 'Box Plot':
                    if is_numeric:
                        fig = px.box(data_df, y=column_to_analyze, title=f"Box Plot of {column_to_analyze}")
                        st.plotly_chart(fig, width='stretch', config={'toImageButtonOptions': {'scale': 3}})
                    else:
                        st.warning("Box Plot is only available for numeric columns.")

                elif analysis_type == 'Value Counts':
                    st.markdown("#### Value Counts Parameters")
                    top_n = st.slider("Number of top values to display", min_value=5, max_value=100, value=20,
                                      key="value_counts_top_n")
                    counts = col_data.value_counts().nlargest(top_n).reset_index()
                    counts.columns = [column_to_analyze, 'count']
                    fig = px.bar(counts, x=column_to_analyze, y='count',
                                 title=f"Top {top_n} Value Counts for {column_to_analyze}")
                    fig.update_xaxes(type='category')
                    st.plotly_chart(fig, width='stretch', config={'toImageButtonOptions': {'scale': 3}})

                    st.write(col_data.value_counts().reset_index())

                elif analysis_type == 'Value Plot':
                    st.markdown("#### Plot Parameters")
                    plot_type = st.radio("Plot Type", ['Line', 'Scatter'], key="value_plot_type")

                    if plot_type == 'Line':
                        fig = px.line(data_df, y=column_to_analyze, title=f"Value Plot of {column_to_analyze}")
                    else:
                        fig = px.scatter(data_df, y=column_to_analyze, title=f"Value Plot of {column_to_analyze}")

                    fig.update_xaxes(title_text='Index')
                    st.plotly_chart(fig, width='stretch', config={'toImageButtonOptions': {'scale': 3}})

            else:
                st.subheader("Multi-Column Analysis")

                are_all_numeric = all(pd.api.types.is_numeric_dtype(data_df[col]) for col in columns_to_analyze)

                if are_all_numeric:
                    analysis_options = ['Summary Statistics', 'Correlation Heatmap', 'Value Plot (Line)', 'Box Plot',
                                        'Scatter Matrix']
                else:
                    analysis_options = ['Summary Statistics']
                    st.warning(
                        "Some plots require all selected columns to be numeric. Only summary statistics are available.")

                analysis_type = st.selectbox("Choose an analysis type", options=analysis_options,
                                             key="multi_col_analysis_type")

                st.subheader(f"Analysis of: `{', '.join(columns_to_analyze)}`")

                if analysis_type == 'Summary Statistics':
                    st.write(data_df[columns_to_analyze].describe())

                elif analysis_type == 'Correlation Heatmap':
                    st.info(
                        "A correlation heatmap shows the correlation coefficient between pairs of numeric variables.")
                    corr_matrix = data_df[columns_to_analyze].corr()
                    fig = px.imshow(corr_matrix, text_auto=True, title="Correlation Heatmap",
                                    color_continuous_scale='RdBu_r', zmin=-1, zmax=1)
                    st.plotly_chart(fig, width='stretch', config={'toImageButtonOptions': {'scale': 3}})

                elif analysis_type == 'Value Plot (Line)':
                    fig = px.line(data_df, y=columns_to_analyze, title="Value Plot")
                    fig.update_xaxes(title_text='Index')
                    st.plotly_chart(fig, width='stretch', config={'toImageButtonOptions': {'scale': 3}})

                elif analysis_type == 'Box Plot':
                    fig = px.box(data_df, y=columns_to_analyze, title="Box Plots")
                    st.plotly_chart(fig, width='stretch', config={'toImageButtonOptions': {'scale': 3}})

                elif analysis_type == 'Scatter Matrix':
                    st.info(
                        "A scatter matrix plots every numeric column against every other. It can be slow for many columns.")
                    fig = px.scatter_matrix(data_df, dimensions=columns_to_analyze, title="Scatter Matrix")
                    st.plotly_chart(fig, width='stretch', config={'toImageButtonOptions': {'scale': 3}})

        with tab3:
            st.header("Advanced Filter")

            if "adv_filters" not in st.session_state:
                st.session_state.adv_filters = []
            if "adv_plots" not in st.session_state:
                st.session_state.adv_plots = []

            if st.session_state.adv_filters:
                current_columns = data_df.columns.tolist()
                st.session_state.adv_filters = [
                    f for f in st.session_state.adv_filters if f.get('column') in current_columns
                ]

            columns_to_show = st.multiselect("Select columns to display", data_df.columns.tolist(),
                                             default=data_df.columns.tolist(), key="adv_cols_to_show")

            with st.expander("Filtering Options"):
                def add_adv_filter():
                    st.session_state.adv_filters.append({'column': data_df.columns[0], 'operator': '==', 'value': ''})

                def add_time_filter():
                    period_cols = [col for col in data_df.columns if pd.api.types.is_period_dtype(data_df[col].dtype)]
                    if not period_cols:
                        st.warning("No PeriodIndex columns available for time-based filtering.")
                        return
                    default_col = period_cols[0]
                    st.session_state.adv_filters.append({'column': default_col, 'operator': '==', 'value': '', 'filter_type': 'Component', 'time_component': 'year'})

                def remove_adv_filter(index):
                    st.session_state.adv_filters.pop(index)

                def on_column_change(filter_index):
                    new_column = st.session_state[f'adv_col_{filter_index}']
                    is_time_filter = st.session_state.adv_filters[filter_index].get('filter_type') is not None

                    st.session_state.adv_filters[filter_index] = {'column': new_column, 'operator': '==', 'value': ''}
                    if is_time_filter:
                        st.session_state.adv_filters[filter_index]['filter_type'] = 'Component'
                        st.session_state.adv_filters[filter_index]['time_component'] = 'year'

                col_add_buttons = st.columns(2)
                with col_add_buttons[0]:
                    st.button("Add Filter", on_click=add_adv_filter)
                with col_add_buttons[1]:
                    st.button("Add Time Component Filter", on_click=add_time_filter)

                for i, f in enumerate(st.session_state.adv_filters):
                    filter_cols = st.columns([3, 2, 3, 3, 1]) # Column, Operator, Value, Component, Remove

                    is_time_filter = f.get('filter_type') is not None

                    with filter_cols[0]:
                        all_columns_list = data_df.columns.tolist()
                        column_options = all_columns_list
                        if is_time_filter:
                            column_options = [col for col in all_columns_list if pd.api.types.is_period_dtype(data_df[col].dtype)]
                        
                        st.selectbox("Column", column_options, key=f'adv_col_{i}', 
                                     index=column_options.index(f['column']) if f['column'] in column_options else 0,
                                     on_change=on_column_change, args=(i,))
                    
                    col_name = f['column']
                    col_type = data_df[col_name].dtype

                    if is_time_filter:
                        with filter_cols[3]: # Component
                            f['time_component'] = st.selectbox("Component", ['year', 'month', 'quarter', 'day'], 
                                                               key=f'adv_time_comp_{i}', 
                                                               index=['year', 'month', 'quarter', 'day'].index(f.get('time_component', 'year')))
                    
                    with filter_cols[1]: # Operator
                        operator_options = ['==', '!=', '>', '<', '>=', '<=', 'in', 'not in']
                        f['operator'] = st.selectbox("Operator", operator_options,
                                                     key=f'adv_op_{i}',
                                                     index=operator_options.index(f.get('operator', '==')) if f.get('operator', '==') in operator_options else 0)

                    with filter_cols[2]: # Value
                        source_data = data_df[col_name]
                        if is_time_filter:
                            source_data = getattr(source_data.dt, f['time_component'])
                        
                        unique_vals = source_data.dropna().unique()
                        
                        if len(unique_vals) <= 50 and f['operator'] in ['==', '!=', 'in', 'not in']:
                            options = sorted([str(v) for v in unique_vals])

                            if f['operator'] in ['in', 'not in']:
                                current_val = f.get('value', [])
                                if not isinstance(current_val, list): current_val = [str(current_val)]
                                default_val = [v for v in current_val if v in options]
                                f['value'] = st.multiselect("Value", options=options, key=f"adv_val_{i}_{f.get('time_component')}", default=default_val)
                            else: # '==' or '!='
                                current_val = str(f.get('value', ''))
                                index = 0
                                if current_val in options:
                                    index = options.index(current_val)
                                f['value'] = st.selectbox("Value", options=options, key=f"adv_val_{i}_{f.get('time_component')}", index=index)
                        else:
                            f['value'] = st.text_input("Value", key=f"adv_val_{i}_{f.get('time_component')}", value=f.get('value', ''))

                    with filter_cols[4]: # Remove button
                        st.button("Remove", on_click=remove_adv_filter, args=(i,), key=f'adv_rem_{i}')
            # --- Filtering Logic ---
            filtered_df = data_df.copy()
            for f in st.session_state.adv_filters:
                value_exists = (f.get('value') is not None and f.get('value') != '') or (isinstance(f.get('value'), list) and len(f.get('value')) > 0)

                if value_exists and f.get('column') and f.get('operator'):
                    try:
                        col_name = f['column']
                        col_type = data_df[col_name].dtype
                        value = f['value']
                        operator = f['operator']

                        if f.get('filter_type') == 'Component' and pd.api.types.is_period_dtype(col_type):
                            component = f['time_component']
                            accessor = filtered_df[col_name].dt
                            
                            if isinstance(value, list):
                                typed_values = pd.Series(value).astype(int).tolist()
                            else:
                                typed_values = int(value)

                            if operator == 'in':
                                filtered_df = filtered_df[getattr(accessor, component).isin(typed_values)]
                            elif operator == 'not in':
                                filtered_df = filtered_df[~getattr(accessor, component).isin(typed_values)]
                            elif operator == '==': 
                                filtered_df = filtered_df[getattr(accessor, component) == typed_values]
                            elif operator == '!=': 
                                filtered_df = filtered_df[getattr(accessor, component) != typed_values]
                            elif operator == '>': 
                                filtered_df = filtered_df[getattr(accessor, component) > typed_values]
                            elif operator == '<': 
                                filtered_df = filtered_df[getattr(accessor, component) < typed_values]
                            elif operator == '>=': 
                                filtered_df = filtered_df[getattr(accessor, component) >= typed_values]
                            elif operator == '<=': 
                                filtered_df = filtered_df[getattr(accessor, component) <= typed_values]

                        elif operator in ['in', 'not in']:
                            if pd.api.types.is_period_dtype(col_type):
                                typed_values = [pd.Period(v, freq=data_df[col_name].dt.freq) for v in value]
                            else:
                                typed_values = pd.Series(value).astype(col_type).tolist()

                            if operator == 'in':
                                filtered_df = filtered_df[filtered_df[col_name].isin(typed_values)]
                            else:
                                filtered_df = filtered_df[~filtered_df[col_name].isin(typed_values)]
                        else:
                            val_for_query = value
                            if pd.api.types.is_numeric_dtype(col_type):
                                try:
                                    val_for_query = pd.to_numeric(value)
                                except (ValueError, TypeError):
                                    st.error(f"Invalid numeric value for column '{col_name}': {value}")
                                    continue
                            elif pd.api.types.is_period_dtype(col_type):
                                try:
                                    val_for_query = pd.Period(value, freq=data_df[col_name].dt.freq)
                                except (ValueError, TypeError):
                                    st.error(f"Invalid period value for column '{col_name}': {value}")
                                    continue
                            
                            query_str = f"`{col_name}` {operator} @val_for_query"
                            filtered_df = filtered_df.query(query_str)
                    except Exception as e:
                        st.error(f"Filter error on column '{f['column']}': {e}")

            st.subheader("Filtered Data")
            st.dataframe(filtered_df[columns_to_show])
            st.subheader("Filtered Data Summary")
            if columns_to_show:
                st.write(filtered_df[columns_to_show].describe())
            else:
                st.info("Select columns to see a summary.")

            with st.expander("Plotting Options", expanded=True):
                def add_adv_plot():
                    st.session_state.adv_plots.append(1)

                def remove_adv_plot(index):
                    st.session_state.adv_plots.pop(index)

                st.button("Add Plot", on_click=add_adv_plot, key="add_adv_plot_btn")
                if not filtered_df.empty and columns_to_show:
                    for i in range(len(st.session_state.adv_plots)):
                        st.markdown(f"--- Plot {i + 1} ---")
                        display_plot(filtered_df, columns_to_show, f"adv_plot_{i}")
                        st.button("Remove Plot", on_click=remove_adv_plot, args=(i,), key=f"remove_adv_plot_{i}")

        with tab4:
            st.header("Interactive Pivot Table")
            st.info("Create a pivot table to summarize and reorganize your data.")

            all_columns = data_df.columns.tolist()
            numeric_columns = [col for col in all_columns if pd.api.types.is_numeric_dtype(data_df[col])]

            pivot_rows = st.multiselect("Select Row(s)", options=all_columns, key="pivot_rows")
            pivot_cols = st.multiselect("Select Column(s)", options=all_columns, key="pivot_cols")

            if not numeric_columns:
                st.warning(
                    "No numeric columns available to aggregate. Pivot table requires at least one numeric 'Values' column.")
                pivot_vals = []
            else:
                pivot_vals = st.multiselect("Select Value(s) to Aggregate", options=numeric_columns, key="pivot_vals")

            agg_func_options = ['mean', 'sum', 'count', 'median', 'min', 'max', 'std']
            pivot_agg = st.selectbox("Select Aggregation Function", options=agg_func_options, key="pivot_agg")

            if st.button("Generate Pivot Table", key="generate_pivot"):
                if not pivot_rows or not pivot_vals:
                    st.error("Please select at least one 'Row' and one 'Value' to generate a pivot table.")
                else:
                    try:
                        st.subheader("Pivot Table Result")
                        pivot_df = pd.pivot_table(
                            data_df,
                            index=pivot_rows,
                            columns=pivot_cols if pivot_cols else None,
                            values=pivot_vals,
                            aggfunc=pivot_agg
                        )
                        st.dataframe(pivot_df.reset_index())
                    except Exception as e:
                        st.error(f"Error generating pivot table: {e}")

        with tab5:
            st.header("Data Cleaning Tools")

            if 'cleaned_df' not in st.session_state or st.session_state.cleaned_df is None:
                st.session_state.cleaned_df = st.session_state.data_df.copy()

            df_to_clean = st.session_state.cleaned_df

            st.subheader("Current Data")
            st.dataframe(df_to_clean)

            st.subheader("Cleaning Actions")

            with st.expander("Handle Missing Values"):
                st.markdown("#### Missing Value Analysis")
                missing_summary = df_to_clean.isna().sum()
                missing_summary = missing_summary[missing_summary > 0]

                if missing_summary.empty:
                    st.success("No missing values found!")
                else:
                    st.write("Columns with missing values:")
                    missing_df = pd.DataFrame({'Column': missing_summary.index, 'Number of Missing Values': missing_summary.values})
                    st.dataframe(missing_df)
                    st.bar_chart(missing_df.set_index('Column'))

                st.markdown("#### Apply a cleaning action")
                all_columns_mv = df_to_clean.columns.tolist()
                col_to_clean = st.selectbox("1. Select a column to clean", options=all_columns_mv, key="clean_col")

                if col_to_clean:
                    is_numeric = pd.api.types.is_numeric_dtype(df_to_clean[col_to_clean])
                    action_options = ["Drop rows with missing values"]
                    if is_numeric:
                        action_options.extend(
                            ["Fill with mean", "Fill with median", "Fill with mode", "Fill with custom value"])
                    else:
                        action_options.extend(["Fill with mode", "Fill with custom value"])

                    action = st.selectbox("2. Choose an action", options=action_options, key="clean_action")
                    custom_value = st.text_input("Enter custom value (if applicable)",
                                                 key="clean_custom_val") if "custom" in action else None

                    if st.button("Apply Missing Value Action", key="apply_clean"):
                        try:
                            if action == "Drop rows with missing values":
                                st.session_state.cleaned_df = df_to_clean.dropna(subset=[col_to_clean])
                            elif action == "Fill with mean":
                                fill_val = df_to_clean[col_to_clean].mean()
                                st.session_state.cleaned_df[col_to_clean] = df_to_clean[col_to_clean].fillna(fill_val)
                            elif action == "Fill with median":
                                fill_val = df_to_clean[col_to_clean].median()
                                st.session_state.cleaned_df[col_to_clean] = df_to_clean[col_to_clean].fillna(fill_val)
                            elif action == "Fill with mode":
                                fill_val = df_to_clean[col_to_clean].mode()[0]
                                st.session_state.cleaned_df[col_to_clean] = df_to_clean[col_to_clean].fillna(fill_val)
                            elif action == "Fill with custom value":
                                if custom_value is not None and custom_value != '':
                                    original_dtype = df_to_clean[col_to_clean].dtype
                                    val_to_fill = pd.Series([custom_value]).astype(original_dtype)[0]
                                    st.session_state.cleaned_df[col_to_clean] = df_to_clean[col_to_clean].fillna(
                                        val_to_fill)
                                else:
                                    st.error("Please provide a custom value.")
                                    st.stop()
                            st.success(f"Action '{action}' applied to column '{col_to_clean}'.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to apply action: {e}")

            with st.expander("Delete Rows"):
                rows_to_delete = st.multiselect("Select rows to delete by index", options=df_to_clean.index.tolist())
                if st.button("Delete Selected Rows"):
                    if rows_to_delete:
                        st.session_state.cleaned_df = df_to_clean.drop(index=rows_to_delete)
                        st.success(f"Deleted {len(rows_to_delete)} row(s).")
                        st.rerun()
                    else:
                        st.warning("No rows selected to delete.")

            with st.expander("Set Row as Header"):
                row_as_header = st.selectbox("Select a row to set as the new header",
                                             options=['-'] + df_to_clean.index.tolist())
                if st.button("Set as Header"):
                    if row_as_header != '-':
                        new_header = df_to_clean.iloc[row_as_header].astype(str)
                        new_df = df_to_clean.copy()
                        new_df.columns = new_header
                        new_df.columns.name = None
                        new_df = new_df.drop(row_as_header)
                        st.session_state.cleaned_df = new_df
                        st.success(f"Row {row_as_header} set as new header.")
                        st.rerun()
                    else:
                        st.warning("No row selected.")

            with st.expander("Rename Columns"):
                cols_to_rename = st.multiselect("Select columns to rename", options=df_to_clean.columns.tolist())
                new_names = {}
                for col in cols_to_rename:
                    new_names[col] = st.text_input(f"New name for '{col}'", value=col)

                if st.button("Rename Selected Columns"):
                    if new_names:
                        if len(set(new_names.values())) != len(new_names.values()):
                            st.error("New column names must be unique.")
                        else:
                            st.session_state.cleaned_df = df_to_clean.rename(columns=new_names)
                            st.success("Columns renamed.")
                            st.rerun()
                    else:
                        st.warning("No columns selected to rename.")

            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Confirm and Overwrite Original Data"):
                    st.session_state.data_df = st.session_state.cleaned_df.copy()
                    st.success("Data has been updated!")
                    st.rerun()
            with col2:
                if st.button("Reset Cleaning"):
                    st.session_state.cleaned_df = st.session_state.data_df.copy()
                    st.info("Cleaning has been reset.")
                    st.rerun()

    else:
        st.markdown(
            """
            <div style="text-align: center;">
                <p class="rainbow-static-text" style="font-family: 'Comic Sans MS', cursive, sans-serif; font-size: 1.2em;">Your interactive tool for viewing, analyzing, and cleaning your data.</p>
            </div>
            <style>
                .rainbow-static-text {
                    background: linear-gradient(to right, #8E2DE2, #4A00E0, #00C6FF, #0072FF, #00F260);
                    -webkit-background-clip: text;
                    background-clip: text;
                    color: transparent;
                }
            </style>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("---")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown(
                """
                ### 💡 What you can do:
                - **Connect to your data:** Upload CSV or Excel files, or connect to a SQLite database.
                - **Explore your data:** View your data in a table, get summary statistics, and analyze columns.
                - **Create interactive plots:** Build line charts, bar charts, scatter plots, and more.
                - **Clean your data:** Handle missing values, remove duplicates, and more.
                - **Create pivot tables:** Summarize your data with interactive pivot tables.
                """
            )

        with col2:
            with open("bouncing_balls.html", "r") as f:
                components.html(f.read(), height=200)

        st.markdown("---")

        st.info("To get started, please connect to a data source using the sidebar on the left.")
        st.markdown(
            """
            *Your data is NOT logged, saved, or used in any way except to presented here.*
            """
        )


if __name__ == "__main__":
    mode = 'server'
    # mode = 'local'
    main(mode=mode)