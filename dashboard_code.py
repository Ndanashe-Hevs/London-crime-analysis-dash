"""
Created on Sat Nov 23 20:27:01 2024

@author: ndanashe
"""

import dash
from dash import dcc, html, Input, Output, dash_table
import plotly.express as px
import plotly.graph_objects as go
import geopandas as gpd
import pandas as pd
import warnings
import socket

# Load dataset
file_path = 'updated_crime_data_with_rate.csv'
geojson_path = 'london-boroughs_1179 (1).geojson'



# Suppress specific UserWarnings
warnings.filterwarnings("ignore", message="Geometry is in a geographic CRS. Results from 'centroid' are likely incorrect.")
 

# Load crime data
crime_data = pd.read_csv(file_path)

# Data Preparation: Add 'Season' column
def get_season(month):
    if month in [12, 1, 2]:
        return "Winter"
    elif month in [3, 4, 5]:
        return "Spring"
    elif month in [6, 7, 8]:
        return "Summer"
    else:
        return "Autumn"

crime_data['Season'] = crime_data['Month'].apply(get_season)

# Group data for Borough Analysis
borough_data = crime_data.groupby('Boroughs', as_index=False).agg({
    'CrimeCount': 'sum',
    'CrimeRatePer1000': 'mean'
})

# Group data for Seasonal Analysis
seasonal_data = crime_data.groupby(['Boroughs', 'Season'], as_index=False).agg({
    'CrimeCount': 'sum',
    'CrimeRatePer1000': 'mean'
})

# Group data for Yearly Trends
yearly_data = crime_data.groupby(['Year', 'MajorCrime'], as_index=False).agg({
    'CrimeCount': 'sum',
    'CrimeRatePer1000': 'mean'
})

# Load GeoJSON data
geo_df = gpd.read_file(geojson_path)

# Aggregate Crime Data to Borough Level
borough_level_data = crime_data.groupby('Boroughs', as_index=False).agg({
    'Population': 'mean',
    'CrimeCount': 'sum',
    'CrimeRatePer1000': 'mean'
})

# Standardize borough names for merging
geo_df['name'] = geo_df['name'].str.strip().str.lower()
borough_level_data['Boroughs'] = borough_level_data['Boroughs'].str.strip().str.lower()

# Merge GeoJSON and Crime Data
merged_geo_df = geo_df.merge(borough_level_data, left_on='name', right_on='Boroughs')

# Extract centroids for text placement
merged_geo_df['centroid_lat'] = merged_geo_df.geometry.centroid.y
merged_geo_df['centroid_lon'] = merged_geo_df.geometry.centroid.x



# Convert GeoDataFrame to GeoJSON format for Plotly
geojson_data = merged_geo_df.__geo_interface__

# Create Map with Borough Names
fig = px.choropleth_mapbox(
    merged_geo_df,
    geojson=geojson_data,
    locations="name",  # Column with borough names
    featureidkey="properties.name",  # Match GeoJSON feature property
    color="CrimeRatePer1000",  # Column to color by
    color_continuous_scale="teal",
    mapbox_style="carto-positron",
    title="Crime Rates Across London Boroughs",
    center={"lat": 51.509865, "lon": -0.118092},  # London's coordinates
    zoom=9
)

# Add Borough Names as Text Annotations
for _, row in merged_geo_df.iterrows():
    fig.add_trace(go.Scattermapbox(
        lat=[row['centroid_lat']],
        lon=[row['centroid_lon']],
        mode='text',
        text=row['name'].title(),  # Capitalize borough names
        textfont=dict(
            size=12,
            color='black'
        ),
        showlegend=False  # Do not show in legend
    ))

# Initialize Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)

# App layout
app.layout = html.Div([
    html.H1("London Crime Dashboard"),
    dcc.Tabs([
        # Borough Analysis Tab
        dcc.Tab(label="Borough Analysis", children=[
            html.Div([
                html.H3("Crime by Borough"),
                dcc.Graph(
                    id='borough-crime-bar-chart',
                    figure=px.bar(
                        borough_data,
                        x='Boroughs',
                        y='CrimeCount',
                        color='CrimeRatePer1000',
                        title="Crime Counts and Rates by Borough",
                        labels={'CrimeCount': 'Crime Count', 'CrimeRatePer1000': 'Crime Rate per 1,000'},
                        template='plotly'
                    )
                ),
            ]),
            html.Div([
                html.H3("Crime Distribution Across Boroughs (Pie Chart)"),
                dcc.Graph(
                    id='borough-pie-chart',
                    figure=px.pie(
                        borough_data,
                        names='Boroughs',
                        values='CrimeCount',
                        title="Crime Distribution by Borough",
                        labels={'Boroughs': 'Borough', 'CrimeCount': 'Crime Count'},
                        template='plotly'
                    )
                ),
            ]),
        ]),
        # Seasonal Crime Patterns Tab
        dcc.Tab(label="Seasonal Crime Patterns", children=[
            html.Div([
                html.H3("Seasonal Crime Patterns Across Boroughs"),
                dcc.Dropdown(
                    id='borough-dropdown',
                    options=[{'label': 'All Boroughs', 'value': 'All'}] +
                            [{'label': borough, 'value': borough} for borough in crime_data['Boroughs'].unique()],
                    value='All',
                    clearable=False
                ),
                dcc.Graph(id='seasonal-crime-pattern-graph')
            ])
        ]),
        # Yearly Trends Tab
        dcc.Tab(label="Yearly Trends", children=[
            html.Div([
                html.H3("Yearly Crime Trends"),
                dcc.Graph(
                    id='yearly-trends-graph',
                    figure=px.line(
                        yearly_data,
                        x='Year',
                        y='CrimeRatePer1000',
                        color='MajorCrime',
                        title="Yearly Trends of Crime Rates by Major Crime Type",
                        labels={'CrimeRatePer1000': 'Crime Rate per 1,000', 'MajorCrime': 'Major Crime'},
                        template='plotly'
                    )
                )
            ])
        ]),
        # Crime Type Analysis Tab
        dcc.Tab(label="Crime Type Analysis", children=[
            html.Div([
                html.H3("Compare Crime Types Across Boroughs"),
                html.Div([
                    html.Label("Select Crime Type:"),
                    dcc.Dropdown(
                        id='crime-type-dropdown',
                        options=[{'label': crime, 'value': crime} for crime in crime_data['MajorCrime'].unique()],
                        value=crime_data['MajorCrime'].unique()[0],
                        clearable=False
                    ),
                ], style={'margin-bottom': '20px'}),
                html.Div([
                    html.Label("Select Boroughs:"),
                    dcc.Dropdown(
                        id='borough-comparison-dropdown',
                        options=[{'label': borough, 'value': borough} for borough in crime_data['Boroughs'].unique()],
                        value=crime_data['Boroughs'].unique()[:3],  # Pre-select first 3 boroughs
                        multi=True,
                        clearable=False
                    ),
                ], style={'margin-bottom': '20px'}),
                html.Div([
                    dcc.Graph(id='borough-comparison-bar-chart')
                ])
            ])
        ]),
        # Statistics and Table Tab
        dcc.Tab(label="Statistics and Table", children=[
            html.Div([
                html.H3("Interactive Crime Statistics"),
                html.Label("Select Crime Type:"),
                dcc.Dropdown(
                    id='crime-type-dropdown-stats',
                    options=[{'label': crime, 'value': crime} for crime in crime_data['MajorCrime'].unique()],
                    value=crime_data['MajorCrime'].unique()[0],
                    clearable=False
                ),
                html.Div(id='statistics-content'),  # Placeholder for statistics
                html.H3("Crime Data Table"),
                dash_table.DataTable(
                    id='crime-data-table',
                    columns=[
                        {"name": col, "id": col} for col in ['Boroughs', 'CrimeCount', 'CrimeRatePer1000']
                    ],
                    style_table={'overflowX': 'auto'},
                    style_cell={'textAlign': 'left'},
                    page_size=10  # Number of rows per page
                )
            ])
        ]),
        # Geospatial Map Tab
        dcc.Tab(label="Geospatial Map", children=[
            html.Div([
                html.H3("Geospatial Map of Borough Crime Data"),
                dcc.Graph(id='crime-choropleth-map', figure=fig)
            ])
        ]),
    ])
])

# Callbacks for interactivity
@app.callback(
    Output('seasonal-crime-pattern-graph', 'figure'),
    Input('borough-dropdown', 'value')
)
def update_seasonal_graph(selected_borough):
    if selected_borough == 'All':
        filtered_data = seasonal_data.groupby('Season', as_index=False).agg({
            'CrimeCount': 'sum',
            'CrimeRatePer1000': 'mean'
        })
        title = "Seasonal Crime Patterns Across All Boroughs"
    else:
        filtered_data = seasonal_data[seasonal_data['Boroughs'] == selected_borough]
        title = f"Seasonal Crime Patterns in {selected_borough}"

    fig = px.bar(
        filtered_data,
        x='Season',
        y='CrimeCount',
        color='Season',
        title=title,
        labels={'CrimeCount': 'Crime Count'},
        template='plotly'
    )
    return fig


@app.callback(
    Output('borough-comparison-bar-chart', 'figure'),
    [Input('crime-type-dropdown', 'value'),
     Input('borough-comparison-dropdown', 'value')]
)
def update_borough_comparison(selected_crime_type, selected_boroughs):
    filtered_data = crime_data[
        (crime_data['MajorCrime'] == selected_crime_type) &
        (crime_data['Boroughs'].isin(selected_boroughs))
    ].groupby('Boroughs', as_index=False).agg({'CrimeCount': 'sum'})

    fig = px.bar(
        filtered_data,
        x='Boroughs',
        y='CrimeCount',
        title=f"Crime Count for '{selected_crime_type}' Across Selected Boroughs",
        labels={'CrimeCount': 'Crime Count', 'Boroughs': 'Borough'},
        template='plotly'
    )
    return fig


@app.callback(
    [Output('statistics-content', 'children'),
     Output('crime-data-table', 'data')],
    Input('crime-type-dropdown-stats', 'value')
)
def update_statistics_and_table(selected_crime_type):
    # Filter data by selected crime type
    filtered_data = crime_data[crime_data['MajorCrime'] == selected_crime_type]
    
    # Calculate statistics
    total_crimes = filtered_data['CrimeCount'].sum()
    average_crime_rate = filtered_data['CrimeRatePer1000'].mean()
    most_affected_borough = filtered_data.groupby('Boroughs')['CrimeCount'].sum().idxmax()
    highest_crime_rate = filtered_data.groupby('Boroughs')['CrimeRatePer1000'].mean().max()

    # Create statistics content
    statistics = html.Ul([
        html.Li(f"Total Crimes: {total_crimes}"),
        html.Li(f"Average Crime Rate (per 1000): {average_crime_rate:.2f}"),
        html.Li(f"Most Affected Borough: {most_affected_borough}"),
        html.Li(f"Highest Crime Rate (per 1000): {highest_crime_rate:.2f}")
    ])

    # Prepare table data
    table_data = filtered_data.groupby('Boroughs', as_index=False).agg({
        'CrimeCount': 'sum',
        'CrimeRatePer1000': 'mean'
    }).to_dict('records')

    return statistics, table_data


@app.callback(
    Output('crime-choropleth-map', 'figure'),
    Input('crime-type-dropdown-map', 'value')
)
def update_geospatial_map(selected_crime_type):
    # Filter the data based on the selected crime type
    filtered_data = crime_data[crime_data['MajorCrime'] == selected_crime_type]
    
    # Aggregate data for the filtered crime type
    borough_level_filtered = filtered_data.groupby('Boroughs', as_index=False).agg({
        'Population': 'mean',
        'CrimeCount': 'sum',
        'CrimeRatePer1000': 'mean'
    })

    # Merge with GeoJSON
    merged_filtered = geo_df.merge(borough_level_filtered, left_on='name', right_on='Boroughs')

    # Create the updated map
    fig = px.choropleth_mapbox(
        merged_filtered,
        geojson=geojson_data,
        locations="name",  # Column with borough names
        featureidkey="properties.name",  # Match GeoJSON feature property
        color="CrimeRatePer1000",  # Column to color by
        color_continuous_scale="teal",
        mapbox_style="carto-positron",
        title=f"Crime Rates Across London Boroughs: {selected_crime_type}",
        center={"lat": 51.509865, "lon": -0.118092},  # London's coordinates
        zoom=9
    )

    # Add Borough Names as Text Annotations
    for _, row in merged_filtered.iterrows():
        fig.add_trace(go.Scattermapbox(
            lat=[row['geometry'].centroid.y],
            lon=[row['geometry'].centroid.x],
            mode='text',
            text=row['name'].title(),
            textfont=dict(
                size=12,
                color='black'
            ),
            showlegend=False
        ))

    return fig


PORT = 8050  # Change this to any preferred port
print(f"Dash app is running at http://127.0.0.1:{PORT}/")
app.run_server(debug=True, host='127.0.0.1', port=PORT)


